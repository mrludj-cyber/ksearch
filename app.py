from flask import Flask, render_template_string, request, jsonify, Response, stream_with_context
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

app = Flask(__name__)

# 타겟 사이트 정보
BASE_URL = "https://yadong7.com"
LIST_URL = f"{BASE_URL}/korea"

# 크롤링 및 다운로드 시 차단 방지를 위한 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": BASE_URL  # 리퍼러 추가 (차단 방지)
}

# 파일명에 사용할 수 없는 특수문자 제거 함수
def clean_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title).strip()

# HTML 템플릿
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko" data-bs-theme="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Personal Korea Video Player</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
    <style>
        body { background-color: #121212; color: #e0e0e0; }
        .card { background-color: #1e1e1e; border: none; margin-bottom: 20px; transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); }
        .card-img-top { height: 180px; object-fit: cover; cursor: pointer; }
        .card-title { font-size: 0.9rem; margin-top: 10px; height: 40px; overflow: hidden; }
        .btn-download { width: 100%; margin-top: 5px; }
        .pagination-container { margin-top: 30px; margin-bottom: 50px; text-align: center; }
        .best-list li { padding: 5px 0; border-bottom: 1px solid #333; cursor: pointer; }
        .best-list li:hover { color: #fe1117; }
        .loading { text-align: center; padding: 50px; display: none; }
        .modal-body iframe { width: 100%; height: 400px; border: none; }
    </style>
</head>
<body>

<div class="container mt-4">
    <h1 class="text-center mb-4"><span style="color:#fe1117;">MY</span> VIDEO APP</h1>

    <!-- 주간/월간 베스트 섹션 -->
    <div class="row mb-5">
        <div class="col-md-6">
            <div class="card p-3">
                <h5>🏆 주간 베스트</h5>
                <ul class="list-unstyled best-list" id="weekly-best"><li>로딩 중...</li></ul>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card p-3">
                <h5>🏆 월간 베스트</h5>
                <ul class="list-unstyled best-list" id="monthly-best"><li>로딩 중...</li></ul>
            </div>
        </div>
    </div>

    <!-- 리스트 섹션 -->
    <h3 class="mb-3">📺 한국야동 리스트 (Page: <span id="current-page">1</span>)</h3>
    <div id="video-grid" class="row row-cols-2 row-cols-md-4 g-3"></div>
    
    <div class="loading" id="loading-spinner">
        <div class="spinner-border text-danger" role="status"></div>
    </div>

    <div class="pagination-container btn-group" role="group" id="pagination-box"></div>
</div>

<!-- 비디오 플레이어 모달 -->
<div class="modal fade" id="videoModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content bg-dark">
            <div class="modal-header border-secondary">
                <h5 class="modal-title" id="modalTitle">영상 재생</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body text-center">
                <div id="player-container">
                    <div class="spinner-border text-light mt-5 mb-5" role="status"></div>
                </div>
                <div class="mt-3 d-grid gap-2">
                    <!-- 진짜 다운로드 버튼 -->
                    <a id="modal-download-btn" href="#" class="btn btn-success btn-lg">
                        <i class="bi bi-download"></i> 내 컴퓨터로 저장하기 (파일명 자동변환)
                    </a>
                    <small class="text-muted">* 다운로드 버튼을 누르면 서버를 통해 변환 후 다운로드가 시작됩니다. 잠시만 기다려주세요.</small>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    let currentPage = 1;

    document.addEventListener('DOMContentLoaded', () => { fetchData(currentPage); });

    async function fetchData(page) {
        document.getElementById('video-grid').innerHTML = '';
        document.getElementById('loading-spinner').style.display = 'block';
        
        try {
            const response = await fetch(`/api/list?page=${page}`);
            const data = await response.json();
            
            renderBest('weekly-best', data.weekly);
            renderBest('monthly-best', data.monthly);
            renderMainList(data.main);
            renderPagination(page);
            document.getElementById('current-page').innerText = page;
        } catch (error) {
            console.error('Error:', error);
        } finally {
            document.getElementById('loading-spinner').style.display = 'none';
        }
    }

    function renderBest(elementId, list) {
        const container = document.getElementById(elementId);
        container.innerHTML = '';
        list.forEach((item, index) => {
            const li = document.createElement('li');
            li.innerHTML = `<span class="badge bg-danger me-2">${index+1}</span> ${item.title}`;
            li.onclick = () => playVideo(item.link, item.title);
            container.appendChild(li);
        });
    }

    function renderMainList(list) {
        const grid = document.getElementById('video-grid');
        grid.innerHTML = '';
        list.forEach(item => {
            const col = document.createElement('div');
            col.className = 'col';
            col.innerHTML = `
                <div class="card h-100">
                    <img src="${item.thumb}" class="card-img-top" alt="${item.title}" onclick="playVideo('${item.link}', '${item.title}')">
                    <div class="card-body p-2 d-flex flex-column justify-content-between">
                        <div class="card-title text-truncate">${item.title}</div>
                        <button class="btn btn-sm btn-outline-danger w-100" onclick="playVideo('${item.link}', '${item.title}')">
                            ▶ 재생 및 다운로드
                        </button>
                    </div>
                </div>
            `;
            grid.appendChild(col);
        });
    }

    async function playVideo(url, title) {
        const modalElement = new bootstrap.Modal(document.getElementById('videoModal'));
        document.getElementById('modalTitle').innerText = title;
        document.getElementById('player-container').innerHTML = '<div class="spinner-border text-light mt-5 mb-5"></div>';
        
        // 다운로드 버튼 초기화 (비활성화)
        const downBtn = document.getElementById('modal-download-btn');
        downBtn.classList.add('disabled');
        downBtn.href = "#";
        
        modalElement.show();

        try {
            const response = await fetch(`/api/video?url=${encodeURIComponent(url)}`);
            const data = await response.json();
            
            if(data.video_src) {
                // iframe 삽입
                document.getElementById('player-container').innerHTML = `
                    <iframe src="${data.video_src}" allowfullscreen></iframe>
                `;
                
                // 프록시 다운로드 링크 생성
                // /api/download?url=비디오주소&title=제목
                const downloadUrl = `/api/download?url=${encodeURIComponent(data.video_src)}&title=${encodeURIComponent(title)}`;
                
                downBtn.href = downloadUrl;
                downBtn.classList.remove('disabled');
            } else {
                document.getElementById('player-container').innerHTML = '<p class="text-danger">영상을 찾을 수 없습니다.</p>';
            }
        } catch (e) {
            document.getElementById('player-container').innerHTML = '<p class="text-danger">로딩 에러 발생</p>';
        }
    }

    function renderPagination(current) {
        const container = document.getElementById('pagination-box');
        container.innerHTML = '';
        
        const createBtn = (text, targetPage, color='btn-secondary') => {
            if (targetPage < 1) return;
            const btn = document.createElement('button');
            btn.className = `btn ${color}`;
            btn.innerText = text;
            btn.onclick = () => { currentPage = targetPage; fetchData(currentPage); };
            container.appendChild(btn);
        };

        createBtn('<<', 1);
        createBtn('<', current - 1);
        
        const currentSpan = document.createElement('button');
        currentSpan.className = 'btn btn-danger disabled';
        currentSpan.innerText = current;
        container.appendChild(currentSpan);

        createBtn('>', current + 1);
        createBtn('+10', current + 10);
    }
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/list')
def get_list():
    page = request.args.get('page', 1)
    target_url = f"{LIST_URL}?page={page}"
    
    try:
        res = requests.get(target_url, headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        data = { "weekly": [], "monthly": [], "main": [] }

        best_boxes = soup.select('.best-box')
        if len(best_boxes) >= 1:
            for item in best_boxes[0].select('ol li a'):
                data['weekly'].append({ "title": item.text.strip(), "link": item['href'] })
        if len(best_boxes) >= 2:
            for item in best_boxes[1].select('ol li a'):
                data['monthly'].append({ "title": item.text.strip(), "link": item['href'] })

        main_items = soup.select('#video-list > li .item')
        for item in main_items:
            img = item.select_one('img')
            a_tag = item.select_one('a')
            title_tag = item.select_one('.item-title')
            
            if img and a_tag and title_tag:
                thumb = img['src'] if img['src'].startswith('http') else BASE_URL + img['src']
                link = a_tag['href'] if a_tag['href'].startswith('http') else BASE_URL + a_tag['href']
                data['main'].append({
                    "title": title_tag.text.strip(),
                    "thumb": thumb,
                    "link": link
                })
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/video')
def get_video():
    url = request.args.get('url')
    try:
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # iframe src 찾기
        iframes = soup.select('article iframe')
        video_src = ""
        
        # 보통 2번째 iframe에 영상이 있으나, 상황에 따라 1번째일수도 있음
        if len(iframes) >= 2:
            video_src = iframes[1].get('src')
        elif len(iframes) == 1:
            video_src = iframes[0].get('src')
            
        if video_src and video_src.startswith('//'):
            video_src = 'https:' + video_src
            
        return jsonify({"video_src": video_src})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# [중요] 프록시 다운로드 기능 추가
@app.route('/api/download')
def proxy_download():
    video_url = request.args.get('url')
    title = request.args.get('title', 'video')
    
    if not video_url:
        return "URL is required", 400

    # 파일명 정리 (특수문자 제거)
    clean_title = clean_filename(title)
    filename = f"{clean_title}.mp4"

    # 스트리밍 요청 설정
    try:
        # 1. 외부 서버에 동영상 데이터 요청 (stream=True 필수)
        req = requests.get(video_url, headers=HEADERS, stream=True)
        
        # 2. Flask가 브라우저에게 보내줄 헤더 설정
        # Content-Disposition: attachment -> 브라우저가 강제로 다운로드하게 만듦
        # filename -> 우리가 정한 깔끔한 파일명으로 설정
        response_headers = {
            'Content-Disposition': f'attachment; filename="{urllib.parse.quote(filename)}"',
            'Content-Type': req.headers.get('Content-Type', 'video/mp4')
        }

        # 3. 데이터 파이프라이닝 (서버 메모리를 아끼기 위해 조각내서 전달)
        return Response(
            stream_with_context(req.iter_content(chunk_size=1024*1024)), # 1MB 단위 전송
            headers=response_headers
        )
    except Exception as e:
        return f"Download Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
