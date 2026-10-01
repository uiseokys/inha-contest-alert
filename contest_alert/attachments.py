"""Bounded text-only attachments. No OCR, macros, JS or arbitrary URL crawling."""
from __future__ import annotations
import io,re,zipfile,ipaddress,socket
from urllib.parse import urlsplit,urljoin
from xml.etree import ElementTree
from bs4 import BeautifulSoup
LIMIT=5_000_000

def links(html:str,base:str)->list[str]:
    host=urlsplit(base).hostname;out=[]
    for a in BeautifulSoup(html,'html.parser').select('a[href]'):
        u=urljoin(base,a['href']);p=urlsplit(u)
        if p.scheme=='https' and p.hostname==host and not p.username and not p.password and p.port in (None,443) and re.search(r'\.(pdf|hwpx|txt)$',p.path,re.I):
            if u not in out:out.append(u)
    return out[:2]

def extract(blob:bytes,kind:str)->dict:
    if len(blob)>LIMIT:return {'status':'too_large','text':''}
    try:
        if kind=='txt':text=blob.decode('utf-8-sig')
        elif kind=='hwpx':
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                infos=z.infolist()
                if len(infos)>200 or sum(x.file_size for x in infos)>8_000_000 or any(x.file_size>max(1,x.compress_size)*150 for x in infos):return {'status':'too_large','text':''}
                blocks=[]
                for item in infos:
                    if not re.fullmatch(r'Contents/section\d+\.xml',item.filename):continue
                    raw=z.read(item)
                    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():return {'status':'unsafe_document','text':''}
                    root=ElementTree.fromstring(raw)
                    paragraphs=[n for n in root.iter() if n.tag.rsplit('}',1)[-1]=='p']
                    blocks.extend(''.join(n.itertext()) for n in paragraphs)
                text='\n'.join(blocks)
        elif kind=='pdf':
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(blob),strict=False)
            if reader.is_encrypted:return {'status':'encrypted','text':''}
            if len(reader.pages)>20:return {'status':'too_many_pages','text':''}
            blocks=[]
            for page in reader.pages:
                content=page.get_contents()
                if content is not None and len(content.get_data())>8_000_000:return {'status':'too_large','text':''}
                blocks.append(page.extract_text() or '')
            text='\n'.join(blocks)
        else:return {'status':'unsupported','text':''}
        text=text[:100_000].strip()
        return {'status':'ok' if text else 'no_text','text':text}
    except Exception:return {'status':'parse_error','text':''}

def _worker(blob,kind,connection):
    try:
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
            resource.setrlimit(resource.RLIMIT_CPU,(8,8))
        except (ImportError,ValueError,OSError):pass
        connection.send(extract(blob,kind))
    except BaseException:pass
    finally:connection.close()

def bounded_extract(blob:bytes,kind:str)->dict:
    import multiprocessing as mp
    ctx=mp.get_context('spawn');receive,send=ctx.Pipe(duplex=False)
    proc=ctx.Process(target=_worker,args=(blob,kind,send));proc.start();send.close()
    try:
        if receive.poll(12):
            try:return receive.recv()
            except EOFError:return {'status':'parse_error','text':''}
        return {'status':'timeout','text':''}
    finally:
        if proc.is_alive():proc.terminate()
        proc.join(timeout=2);receive.close()

def fetch(client,url:str)->bytes:
    """Same-host attachment fetch; redirects revalidated before every request."""
    from .intake import public_url
    initial=urlsplit(public_url(url)).hostname
    for _ in range(4):
        parsed=urlsplit(public_url(url))
        if parsed.hostname!=initial:raise ValueError('첨부 리다이렉트 호스트 변경')
        addresses=socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):raise ValueError('공개 인터넷 주소가 아닌 첨부는 읽지 않습니다.')
        client._check_robots(url)
        with client.session.get(url,timeout=(6,12),stream=True,allow_redirects=False) as r:
            if r.status_code in (301,302,303,307,308):url=urljoin(url,r.headers.get('Location',''));continue
            if r.status_code!=200:raise ValueError('첨부 접근 실패')
            size=0;chunks=[]
            for chunk in r.iter_content(65536):
                size+=len(chunk)
                if size>LIMIT:raise ValueError('첨부 크기 초과')
                chunks.append(chunk)
            return b''.join(chunks)
    raise ValueError('첨부 리다이렉트 횟수 초과')
