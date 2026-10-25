"""Read selected ZIP members by bounded HTTPS ranges; never import archive code."""
import struct
import zlib
from .common import digest


class RemoteZip:
    def __init__(self,broker,url,size,rights):
        self.broker,self.url,self.size,self.rights=broker,url,size,rights
        self.snapshots=[]
        tail=self.range(max(0,size-65536),size-1)
        e=tail.rfind(b'PK\x05\x06')
        if e<0:raise ValueError('ZIP end record absent')
        disk,cd_disk,n_disk,n,size_cd,offset,comment=struct.unpack_from('<4H2IH',tail,e+4)
        if disk or cd_disk or n_disk!=n or e+22+comment!=len(tail):raise ValueError('Unsupported ZIP layout')
        cd=self.range(offset,offset+size_cd-1);self.members={};i=0
        while i<len(cd):
            if cd[i:i+4]!=b'PK\x01\x02':raise ValueError('Invalid central directory')
            flags,method=struct.unpack_from('<HH',cd,i+8)
            crc,compressed,size=struct.unpack_from('<III',cd,i+16)
            fn,ex,co=struct.unpack_from('<HHH',cd,i+28)
            off=struct.unpack_from('<I',cd,i+42)[0]
            name=cd[i+46:i+46+fn].decode('utf-8')
            if flags&1 or method not in (0,8) or name in self.members:raise ValueError('Unsupported member')
            self.members[name]={'offset':off,'compressed_bytes':compressed,'bytes':size,'crc32':crc,'method':method}
            i+=46+fn+ex+co
        if len(self.members)!=n:raise ValueError('Directory count mismatch')

    def range(self,start,end):
        data,s=self.broker.fetch(self.url,kind='data',items=0,rights=self.rights,byte_range=(start,end))
        if s['content_range'].split('/')[-1]!=str(self.size):raise ValueError('Remote archive size changed')
        self.snapshots.append(s)
        return data

    def read(self,name,max_bytes=50000000):
        item=self.members[name]
        if item['bytes']>max_bytes:raise ValueError('Decompression budget exceeded')
        offset=item['offset'];h=self.range(offset,offset+29)
        if h[:4]!=b'PK\x03\x04':raise ValueError('Local ZIP header mismatch')
        fn,ex=struct.unpack_from('<HH',h,26)
        header=self.range(offset+30,offset+29+fn+ex)
        if header[:fn].decode('utf-8')!=name:raise ValueError('Local filename mismatch')
        start=offset+30+fn+ex;end=start+item['compressed_bytes']
        decompressor=zlib.decompressobj(-15) if item['method']==8 else None
        output=bytearray()
        chunk=self.broker.policy['budgets']['max_response_bytes']
        for pos in range(start,end,chunk):
            data=self.range(pos,min(end,pos+chunk)-1)
            data=decompressor.decompress(data,max_bytes+1-len(output)) if decompressor else data
            output.extend(data)
            if len(output)>max_bytes or (decompressor and decompressor.unconsumed_tail):raise ValueError('Decompression budget exceeded')
        if decompressor:
            output.extend(decompressor.flush())
            if not decompressor.eof or decompressor.unused_data:raise ValueError('Incomplete compressed stream')
        if len(output)!=item['bytes'] or zlib.crc32(output)!=item['crc32']:raise ValueError('Member length/CRC mismatch')
        return bytes(output),{**item,'name':name,'sha256':digest(output),'archive_url':self.url,
            'integrity_scope':'Selected member CRC, length and SHA256; full archive MD5 was not computed'}
