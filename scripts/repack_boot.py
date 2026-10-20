#!/usr/bin/env python3
"""Repack an Ace 5 F.53 kernel with a valid boot-chain AVB structure."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

PACKAGE=Path(__file__).resolve().parents[1]
TOOLS=PACKAGE/'tools/bootimg'
STOCK_SHA='cbf8fb73a79788d9ae8dac0f1fbbeae1d3e936c11089773f41d02c5130ba7d61'
PARTITION_SIZE=201326592

def sha(data): return hashlib.sha256(data).hexdigest()
def require(ok,message):
    if not ok: raise SystemExit(message)
def run(*args):
    return subprocess.check_output([sys.executable,'-X','utf8',*map(str,args)])

def repack(stock,kernel,output):
    stock=stock.resolve(); kernel=kernel.resolve(); output=output.resolve()
    require(output not in (stock,kernel),'Output cannot overwrite input')
    require(not output.exists(),'Output already exists; choose a new output path')
    original=stock.read_bytes(); payload=kernel.read_bytes()
    require(sha(original)==STOCK_SHA,'Stock boot is not the verified Ace 5 F.53 image')
    require(payload[56:60]==b'ARMd','Expected an uncompressed ARM64 Image')
    require(len(original)==PARTITION_SIZE and original[-64:-60]==b'AVBf','Unexpected stock AVB layout')
    require(original[:8]==b'ANDROID!' and struct.unpack_from('<I',original,40)[0]==4,'Unexpected boot header')
    require(struct.unpack_from('<I',original,12)[0]==0,'Unexpected stock ramdisk')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ace5-repack-',dir=output.parent) as tmp:
        work=Path(tmp)
        args=run(TOOLS/'unpack_bootimg.py','--boot_img',stock,'--out',work/'stock','--format','mkbootimg','-0').decode().split('\0')[:-1]
        args[args.index('--kernel')+1]=str(kernel)
        raw=work/'payload.img'
        run(TOOLS/'mkbootimg.py',*args,'--output',raw)
        raw_bytes=raw.read_bytes()
        require(raw_bytes[:8]+raw_bytes[12:4096]==original[:8]+original[12:4096],'Unexpected boot header modification')
        require(raw_bytes[4096:4096+len(payload)]==payload,'Kernel changed during packaging')
        shutil.copyfile(raw,output)
        try:
            run(TOOLS/'avbtool.py','add_hash_footer','--image',output,'--partition_name','boot',
                '--partition_size',PARTITION_SIZE,'--algorithm','NONE','--hash_algorithm','sha256',
                '--salt','a495ab2f4de0bd6b15de636620181a35','--rollback_index','0',
                '--prop','com.android.build.boot.os_version:14',
                '--prop','com.android.build.boot.fingerprint:qti/pineapple/pineapple:14/UKQ1.231108.001/1780913450973:user/release-keys',
                '--prop','com.android.build.boot.security_patch:2026-06-01')
            fixed=output.read_bytes()
            require(len(fixed)==PARTITION_SIZE and fixed[:len(raw_bytes)]==raw_bytes,'Unexpected AVB payload change')
            _,_,_,size,offset,vbsize,_=struct.unpack('>4sIIQQQ28s',fixed[-64:])
            require(fixed[-64:-60]==b'AVBf' and size==len(raw_bytes) and offset>=size and fixed[offset:offset+4]==b'AVB0','Invalid AVB footer')
            verify=work/'verify'; verify.mkdir()
            shutil.copyfile(output,verify/'boot.img')
            verification=run(TOOLS/'avbtool.py','verify_image','--image',verify/'boot.img').decode()
            report={'status':'packaged-and-AVB-structure-verified; new kernel variants still require device tests',
                    'firmware':'PKG110_16.0.8.300(CN01) F.53','image':output.name,'bytes':len(fixed),
                    'sha256':sha(fixed),'stock_boot_sha256':STOCK_SHA,'kernel_sha256':sha(payload),
                    'payload_bytes':len(raw_bytes),'avb_offset':offset,'avb_bytes':vbsize,'avb_algorithm':'NONE',
                    'oem_signed':False,'unlocked_bootloader_required':True,'vbmeta_partition_modified':False,
                    'avb_verification':verification}
            output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(report,indent=2))
        except BaseException:
            output.unlink(missing_ok=True)
            raise

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock-boot',type=Path,required=True)
    parser.add_argument('--kernel',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    repack(a.stock_boot,a.kernel,a.output)
