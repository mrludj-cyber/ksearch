from flask import Flask, render_template_string, request, jsonify, Response
from functools import wraps
import requests
from bs4 import BeautifulSoup
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
app = Flask(__name__)

# ==========================================
# ★ 아이디/비번 설정 (원하는대로 변경 가능)
USERNAME = "admin"
PASSWORD = "43212345"
# ==========================================

BASE_URL = "https://yadong7.com"
LIST_URL = f"{BASE_URL}/korea"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": BASE_URL
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko" data-bs-theme="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
    
    <!-- ★★★ 1. 웹앱 제목 (홈 화면에 추가될 이름) ★★★ -->
    <title>System Monitor</title>

    <!-- ★★★ 2. 아이콘 설정 (차트 모양 📈 으로 위장) ★★★ -->
    <!-- 브라우저 탭 아이콘 -->
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📈</text></svg>">
    <!-- 아이폰/안드로이드 홈 화면 아이콘 -->
    <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect width=%22100%22 height=%22100%22 fill=%22%231e1e1e%22/><text x=%2250%25%22 y=%2255%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-size=%2280%22>📈</text></svg>">

    <!-- ★★★ 3. 주소창 없애기 (앱처럼 보이게) ★★★ -->
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="mobile-web-app-capable" content="yes">

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #121212; color: #e0e0e0; -webkit-tap-highlight-color: transparent; }
        .card { background-color: #1e1e1e; border: none; margin-bottom: 20px; }
        .card-img-top { height: 160px; object-fit: cover; cursor: pointer; }
        .card-title { font-size: 0.85rem; margin-top: 8px; height: 38px; overflow: hidden; }
        /* 베스트 리스트 스타일 */
        .best-container { background: #2c2c2c; border-radius: 10px; padding: 15px; margin-bottom: 20px; }
        .best-title { font-size: 1.1rem; color: #ffca2c; border-bottom: 1px solid #444; padding-bottom: 10px; margin-bottom: 10px; font-weight: bold; }
        .best-list { list-style: none; padding: 0; margin: 0; font-size: 0.9rem; }
        .best-list li { padding: 6px 0; border-bottom: 1px solid #333; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .best-list li:hover { color: #fe1117; }
        .rank-badge { display: inline-block; width: 20px; text-align: center; margin-right: 8px; font-weight: bold; color: #fff; background-color: #dc3545; border-radius: 4px; font-size: 0.8rem; }
        
        /* 페이지네이션 스타일 */
        .pagination-container { margin-top: 30px; margin-bottom: 80px; display: flex; justify-content: center; gap: 5px; flex-wrap: wrap; }
        .btn-page { min-width: 50px; font-weight: bold; }
    </style>
</head>
<body>
<div class="container mt-4">
    <!-- 상단 타이틀 -->
    <h1 class="text-center mb-4" onclick="location.reload()" style="cursor:pointer">
        <span style="color:#fe1117;">SYS</span> MONITOR
    </h1>

    <!-- 1. 주간/월간 베스트 영역 -->
    <div class="row">
        <div class="col-md-6">
            <div class="best-container">
                <div class="best-title">🔥 Weekly Best</div>
                <ul class="best-list" id="weekly-best"><li>Loading...</li></ul>
            </div>
        </div>
        <div class="col-md-6">
            <div class="best-container">
                <div class="best-title">🏆 Monthly Best</div>
                <ul class="best-list" id="monthly-best"><li>Loading...</li></ul>
            </div>
        </div>
    </div>

    <!-- 메인 리스트 -->
    <h4 class="mb-3 mt-2 text-white border-start border-4 border-danger ps-2">Main List (Page: <span id="current-page">1</span>)</h4>
    
    <div id="video-grid" class="row row-cols-2 row-cols-md-4 row-cols-lg-5 g-3">
        <!-- 자바스크립트로 로딩됨 -->
    </div>
    
    <div id="loading" class="text-center py-5"><div class="spinner-border text-danger"></div></div>

    <!-- 2. 페이지네이션 -->
    <div class="pagination-container" id="pagination-box"></div>

</div>

<!-- 비디오 모달 -->
<div class="modal fade" id="vModal" tabindex="-1">
    <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content bg-dark">
            <div class="modal-header border-secondary">
                <h5 class="modal-title text-truncate" id="mTitle" style="max-width: 90%;">Player</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body text-center p-0">
                <div id="p-con" style="background:#000; min-height:400px; display:flex; align-items:center; justify-content:center;">
                    <div class="spinner-border text-light"></div>
                </div>
            </div>
            <div class="modal-footer border-secondary justify-content-center">
                <a id="d-btn" class="btn btn-success w-100" target="_blank">Download / Watch Full</a>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
let currentPage = 1;
let lastPage = 1000;

document.addEventListener('DOMContentLoaded', () => fetchData(1));

async function fetchData(page) {
    currentPage = page;
    document.getElementById('video-grid').innerHTML = '';
    document.getElementById('loading').style.display = 'block';
    window.scrollTo(0,0);
    
    try {
        const res = await fetch(`/api/list?page=${page}`);
        if(res.status === 401) { location.reload(); return; }
        
        const data = await res.json();
        
        renderBest('weekly-best', data.weekly);
        renderBest('monthly-best', data.monthly);
        
        const grid = document.getElementById('video-grid');
        data.main.forEach(item => {
            grid.innerHTML += `
                <div class="col">
                    <div class="card h-100">
                        <img src="${item.thumb}" class="card-img-top" onclick="play('${item.link}', '${item.title}')">
                        <div class="card-body p-2">
                            <div class="card-title">${item.title}</div>
                        </div>
                    </div>
                </div>`;
        });

        if(data.last_page) lastPage = parseInt(data.last_page);
        renderPagination();
        document.getElementById('current-page').innerText = page;

    } catch(e) {
        // 에러 무시
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

function renderBest(id, list) {
    const ul = document.getElementById(id);
    ul.innerHTML = '';
    if(!list || list.length === 0) { ul.innerHTML = '<li>데이터 없음</li>'; return; }
    list.forEach((item, idx) => {
        const li = document.createElement('li');
        li.innerHTML = `<span class="rank-badge">${idx+1}</span> ${item.title}`;
        li.onclick = () => play(item.link, item.title);
        ul.appendChild(li);
    });
}

function renderPagination() {
    const box = document.getElementById('pagination-box');
    box.innerHTML = '';
    const createBtn = (text, target, cls='btn-outline-secondary') => {
        const btn = document.createElement('button');
        btn.className = `btn btn-page ${cls}`;
        btn.innerHTML = text;
        if (target < 1) target = 1;
        if (target > lastPage) target = lastPage;
        if (text === String(currentPage)) {
            btn.className = 'btn btn-page btn-danger';
            btn.disabled = true;
        }
        btn.onclick = () => fetchData(target);
        return btn;
    };
    box.appendChild(createBtn('<i class="bi bi-chevron-double-left"></i>', 1));
    box.appendChild(createBtn('-10', currentPage - 10));
    box.appendChild(createBtn('Prev', currentPage - 1));
    const cur = document.createElement('span');
    cur.className = 'btn btn-danger disabled';
    cur.innerText = currentPage;
    box.appendChild(cur);
    box.appendChild(createBtn('Next', currentPage + 1));
    box.appendChild(createBtn('+10', currentPage + 10));
    box.appendChild(createBtn('<i class="bi bi-chevron-double-right"></i>', lastPage));
}

async function play(url, title) {
    const modal = new bootstrap.Modal(document.getElementById('vModal'));
    document.getElementById('mTitle').innerText = title || 'Video';
    document.getElementById('p-con').innerHTML = '<div class="spinner-border text-light"></div>';
    document.getElementById('d-btn').style.display = 'none';
    modal.show();

    try {
        const res = await fetch(`/api/video?url=${encodeURIComponent(url)}`);
        const data = await res.json();
        if (data.video_src) {
            document.getElementById('p-con').innerHTML = `<iframe src="${data.video_src}" style="width:100%; height:400px; border:none;" allowfullscreen></iframe>`;
            const btn = document.getElementById('d-btn');
            btn.href = data.video_src;
            btn.style.display = 'inline-block';
        }
    } catch (e) {}
}
</script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
</body>
</html>
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
        # SSL 인증서 검증 무시 (verify=False) -> 속도 향상 및 에러 방지
        r = requests.get(f"{LIST_URL}?page={p}", headers=HEADERS, verify=False, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        data = {"weekly": [], "monthly": [], "main": [], "last_page": 1000}

        # 1. 주간/월간 베스트 파싱
        best_boxes = soup.select('.best-box')
        if len(best_boxes) >= 1:
            for item in best_boxes[0].select('ol li'):
                a = item.select_one('a')
                if a: data['weekly'].append({"title": a.text.strip(), "link": a['href']})
        if len(best_boxes) >= 2:
            for item in best_boxes[1].select('ol li'):
                a = item.select_one('a')
                if a: data['monthly'].append({"title": a.text.strip(), "link": a['href']})

        # 2. 메인 리스트 파싱
        for i in soup.select('#video-list > li .item'):
            title_tag = i.select_one('.item-title')
            img_tag = i.select_one('img')
            link_tag = i.select_one('a')
            
            if title_tag and img_tag and link_tag:
                t = title_tag.text.strip()
                src = img_tag['src']
                if not src.startswith('http'): src = BASE_URL + src
                lnk = link_tag['href']
                if not lnk.startswith('http'): lnk = BASE_URL + lnk
                data['main'].append({"title": t, "thumb": src, "link": lnk})

        # 3. 마지막 페이지 번호 찾기 (맨끝 버튼용)
        # .pg_end 클래스를 찾아서 href의 page=숫자 추출
        pg_end = soup.select_one('.pg_end')
        if pg_end and 'href' in pg_end.attrs:
            match = re.search(r'page=(\d+)', pg_end['href'])
            if match:
                data['last_page'] = match.group(1)

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/video')
@requires_auth
def video_api():
    try:
        r = requests.get(request.args.get('url'), headers=HEADERS, verify=False, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # iframe 찾기 (보통 두번째 iframe이 영상임)
        iframes = soup.select('article iframe')
        v = ""
        if len(iframes) >= 2: v = iframes[1].get('src')
        elif len(iframes) == 1: v = iframes[0].get('src')
        
        if v and v.startswith('//'): v = 'https:' + v
        return jsonify({"video_src": v})
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
