from flask import Flask, render_template_string, request, jsonify, Response
from functools import wraps
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
app = Flask(__name__)

# ★ 아이디/비번 설정 ★
USERNAME = "admin"
PASSWORD = "1234"

BASE_URL = "https://yadong7.com"
LIST_URL = f"{BASE_URL}/korea"
HEADERS = {"User-Agent": "Mozilla/5.0"}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko" data-bs-theme="dark">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>System Monitor</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#121212;color:#e0e0e0}.card{background:#1e1e1e;margin-bottom:20px}.card-img-top{height:180px;object-fit:cover}</style>
</head>
<body>
<div class="container mt-4"><h1 class="text-center text-danger">SYS MONITOR</h1>
<div id="video-grid" class="row row-cols-2 row-cols-md-4 g-3"></div>
<div class="d-grid gap-2 mt-4"><button class="btn btn-secondary" onclick="fetchData(currentPage+1)">Next Page</button></div>
</div>
<!-- 모달 -->
<div class="modal fade" id="vModal"><div class="modal-dialog modal-lg"><div class="modal-content bg-dark"><div class="modal-body text-center"><div id="p-con"></div><a id="d-btn" class="btn btn-success mt-3" target="_blank">Download</a></div></div></div></div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
let currentPage=1;
document.addEventListener('DOMContentLoaded',()=>fetchData(1));
async function fetchData(p){
    currentPage=p;
    try{
        const res=await fetch(`/api/list?page=${p}`);
        if(res.status===401){location.reload();return;}
        const data=await res.json();
        const g=document.getElementById('video-grid'); g.innerHTML='';
        data.main.forEach(i=>{
            g.innerHTML+=`<div class="col"><div class="card"><img src="${i.thumb}" class="card-img-top" onclick="play('${i.link}')"><div class="card-body p-2"><div class="small text-truncate">${i.title}</div></div></div></div>`;
        });
    }catch(e){alert('Error');}
}
async function play(u){
    const m=new bootstrap.Modal(document.getElementById('vModal'));m.show();
    const res=await fetch(`/api/video?url=${encodeURIComponent(u)}`);
    const d=await res.json();
    document.getElementById('p-con').innerHTML=`<iframe src="${d.video_src}" style="width:100%;height:400px;border:none" allowfullscreen></iframe>`;
    document.getElementById('d-btn').href=d.video_src;
}
</script></body></html>
"""

def check_auth(u, p): return u == USERNAME and p == PASSWORD
def authenticate(): return Response('Login Required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password): return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/list')
@requires_auth
def list_api():
    p = request.args.get('page', 1)
    try:
        r = requests.get(f"{LIST_URL}?page={p}", headers=HEADERS, verify=False); r.raise_for_status()
        s = BeautifulSoup(r.text, 'html.parser')
        d = []
        for i in s.select('#video-list > li .item'):
            d.append({"title": i.select_one('.item-title').text.strip(), "thumb": i.select_one('img')['src'] if 'http' in i.select_one('img')['src'] else BASE_URL+i.select_one('img')['src'], "link": i.select_one('a')['href'] if 'http' in i.select_one('a')['href'] else BASE_URL+i.select_one('a')['href']})
        return jsonify({"main": d})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/video')
@requires_auth
def video_api():
    try:
        r = requests.get(request.args.get('url'), headers=HEADERS, verify=False)
        s = BeautifulSoup(r.text, 'html.parser')
        v = s.select('article iframe')[1].get('src') if len(s.select('article iframe')) > 1 else s.select('article iframe')[0].get('src')
        if v.startswith('//'): v = 'https:' + v
        return jsonify({"video_src": v})
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == '__main__': app.run(host='0.0.0.0', port=5000)
