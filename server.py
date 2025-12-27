"""
카카오 이모티콘 PlayMCP 서버

카카오톡 이모티콘 제작을 자동화하거나 제작에 도움을 주기 위한 MCP 서버입니다.
PlayMCP에서 호스팅되며, 허깅페이스 계정 연동을 통해 이미지 생성 API를 사용합니다.
"""
import os
from typing import List, Optional

# FastAPI 관련 임포트만 최상위에 유지 (빠른 헬스체크를 위해)
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware


# MCP 관련 전역 변수 (하단에서 초기화)
_mcp = None
_mcp_app = None
_mcp_transport_type = None


def _extract_hf_token_from_headers() -> Optional[str]:
    """
    HTTP 헤더에서 Hugging Face 토큰을 추출합니다.
    Authorization: Bearer <token> 형식을 지원합니다.
    
    Returns:
        추출된 토큰 또는 None
    """
    try:
        from fastmcp.server.dependencies import get_http_headers
        headers = get_http_headers()
        if headers:
            # case-insensitive 헤더 검색
            auth_header = None
            for key, value in headers.items():
                if key.lower() == "authorization":
                    auth_header = value
                    break
            
            if auth_header and auth_header.lower().startswith("bearer "):
                return auth_header[7:].strip()  # "Bearer " 이후의 토큰 부분 추출
    except Exception:
        # 헤더를 가져올 수 없는 경우 (예: HTTP 컨텍스트가 아닌 경우)
        pass
    return None

# FastAPI 앱 생성 (lifespan은 MCP 초기화 후 설정됨)
app = FastAPI(title="카카오 이모티콘 MCP 서버")

# CORS 설정 추가 (외부 MCP 클라이언트 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 (Railway 배포용)"""
    return {"status": "healthy", "service": "kakao-emoticon-mcp"}


@app.get("/.well-known/mcp")
async def mcp_metadata():
    """MCP 서버 메타데이터 엔드포인트 (PlayMCP가 서버 정보를 불러올 때 사용)"""
    return {
        "version": "1.0",
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "kakao-emoticon-mcp",
            "title": "카카오 이모티콘 MCP 서버",
            "version": "1.0.0"
        },
        "description": "카카오톡 이모티콘 제작 자동화 MCP 서버. AI가 사용자에게 질문하지 않고 독립적으로 기획부터 제작까지 전 과정을 자동 수행합니다. (AI autonomously plans and creates emoticons without asking user for details)",
        "transport": {
            "type": "streamable-http",
            "endpoint": "/"
        },
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {},
            "prompts": {}
        },
        "tools": [
            {
                "name": "get_specs_tool",
                "description": "[STEP 0 - CALL FIRST] Get emoticon specs to know required count/format. AI must check this before planning."
            },
            {
                "name": "before_preview_tool",
                "description": "[STEP 1/4] Pre-production Preview - AI creates ALL emoticon descriptions autonomously. DO NOT ask user for ideas."
            },
            {
                "name": "generate_tool",
                "description": "[STEP 2/4] AI Emoticon Generator - Generate images immediately using AI's plan. DO NOT ask for confirmation."
            },
            {
                "name": "after_preview_tool",
                "description": "[STEP 3/4] Final Preview - Show preview automatically. DO NOT ask if user wants to see it."
            },
            {
                "name": "check_tool",
                "description": "[STEP 4/4] Validator - Run automatically after preview. DO NOT ask if user wants validation."
            }
        ]
    }


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "name": "kakao-emoticon-mcp",
        "description": "카카오톡 이모티콘 제작 자동화 MCP 서버",
        "version": "1.0.0",
        "endpoints": {
            "mcp": "/",
            "health": "/health",
            "preview": "/preview/{preview_id}",
            "download": "/download/{download_id}"
        }
    }


@app.get("/preview/{preview_id}", response_class=HTMLResponse)
async def get_preview(preview_id: str):
    """프리뷰 페이지 반환"""
    from src.preview_generator import get_preview_generator
    
    generator = get_preview_generator(os.environ.get("BASE_URL", ""))
    html = generator.get_preview_html(preview_id)
    if html:
        return HTMLResponse(content=html)
    return HTMLResponse(content="Preview not found", status_code=404)


@app.get("/download/{download_id}")
async def get_download(download_id: str):
    """ZIP 파일 다운로드"""
    from src.preview_generator import get_preview_generator
    
    generator = get_preview_generator(os.environ.get("BASE_URL", ""))
    zip_bytes = generator.get_download_zip(download_id)
    if zip_bytes:
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=emoticons.zip"}
        )
    return Response(content="Download not found", status_code=404)


# ===== MCP 도구 등록 함수 (MCP 초기화 전에 정의되어야 함) =====
def _register_tools(mcp):
    """MCP 도구들을 등록"""
    
    @mcp.tool(
        description="""
[STEP 1/4 - Planning Phase] Pre-production Preview Tool (제작 전 프리뷰)

PURPOSE: Generate a KakaoTalk-style chat preview page with TEXT PLACEHOLDERS instead of actual images.

⚠️ AI BEHAVIOR: DO NOT ask user for emoticon descriptions or plans.
AI MUST create all emoticon descriptions and plans AUTONOMOUSLY based on the theme.
Be creative and design a complete emoticon set without user input.

WORKFLOW POSITION: Use this tool FIRST after checking specs.

INPUT:
- emoticon_type: Type of emoticon set (static, dynamic, big, static-mini, dynamic-mini)
- title: Name of the emoticon set (AI decides if not provided)
- plans: Array of {description: string, file_type: string} - AI MUST generate ALL descriptions creatively

OUTPUT:
- preview_url: URL to view the text-based preview in KakaoTalk chat style
- total_count: Number of planned emoticons

EXAMPLE AI BEHAVIOR:
User: "고양이 이모티콘 만들어줘"
AI should: Create 32 unique cat emoticon descriptions like "기지개 펴는 고양이", "하품하는 고양이", "화난 고양이" etc. WITHOUT asking user.
"""
    )
    async def before_preview_tool(
        emoticon_type: str,
        title: str,
        plans: List[dict]
    ) -> dict:
        from src.models import BeforePreviewRequest, EmoticonPlan
        from src.tools import before_preview
        
        request = BeforePreviewRequest(
            emoticon_type=emoticon_type,
            title=title,
            plans=[EmoticonPlan(**p) for p in plans]
        )
        
        response = await before_preview(request)
        return response.model_dump()

    @mcp.tool(
        description="""
[STEP 2/4 - Generation Phase] AI Emoticon Generator (AI 이모티콘 생성기)

PURPOSE: Generate actual emoticon images using AI based on character reference and descriptions.
This is the MAIN PRODUCTION tool that creates the emoticon images.

⚠️ AI BEHAVIOR: Proceed directly to generation WITHOUT asking user for confirmation.
AI should use the descriptions it created in Step 1 and generate immediately.
DO NOT ask user to review or modify the plan - just generate.

WORKFLOW POSITION: Use IMMEDIATELY after before_preview_tool.

INPUT:
- emoticon_type: Type of emoticon (determines size, format, animation)
- emoticons: Array of {description: string, file_extension: string} - use descriptions from planning phase
- character_image (optional): Base64 or URL of reference character. If omitted, AI generates a new character automatically.
- hf_token (optional): Hugging Face API token. Can also be passed via Authorization header (Bearer token).

OUTPUT:
- emoticons: Array of generated images with base64 data, dimensions, file size
- icon: Auto-generated icon image (78x78 PNG) based on first emoticon
- emoticon_type: Confirmed type used for generation

BEHAVIOR:
- Static emoticons (static, static-mini): Generates PNG images
- Animated emoticons (dynamic, dynamic-mini, big): Generates video → converts to animated WebP
- Character is auto-generated if not provided - DO NOT ask user for character image
"""
    )
    async def generate_tool(
        emoticon_type: str,
        emoticons: List[dict],
        character_image: Optional[str] = None,
        hf_token: Optional[str] = None
    ) -> dict:
        from src.models import GenerateRequest, EmoticonGenerateItem
        from src.tools import generate
        
        # Authorization 헤더에서 토큰 추출 시도, 없으면 파라미터 사용
        # 우선순위: Authorization 헤더 > hf_token 파라미터 > 환경변수 HF_TOKEN
        token = _extract_hf_token_from_headers() or hf_token
        
        # 토큰이 없고 환경변수도 없으면 에러 반환
        if not token and not os.environ.get("HF_TOKEN"):
            return {
                "error": "Hugging Face 토큰이 필요합니다.",
                "message": "Authorization 헤더(Bearer 토큰) 또는 hf_token 파라미터로 토큰을 전달해주세요.",
                "token_url": "https://huggingface.co/settings/tokens"
            }
        
        request = GenerateRequest(
            emoticon_type=emoticon_type,
            character_image=character_image,
            emoticons=[EmoticonGenerateItem(**e) for e in emoticons]
        )
        
        response = await generate(request, token)
        return response.model_dump()

    @mcp.tool(
        description="""
[STEP 3/4 - Preview Phase] Final Preview with Real Images (완성본 프리뷰)

PURPOSE: Generate a KakaoTalk-style chat preview page with ACTUAL EMOTICON IMAGES.
Allows user to see how emoticons look in a real chat environment and download them.

⚠️ AI BEHAVIOR: Call this IMMEDIATELY after generate_tool completes.
DO NOT ask user if they want to see preview - always show it automatically.
Provide both preview_url and download_url to user without asking.

WORKFLOW POSITION: Use IMMEDIATELY after generate_tool.

INPUT:
- emoticon_type: Type of emoticon set
- title: Name of the emoticon set
- emoticons: Array of {image_data: base64/URL, frames?: array} for each emoticon
- icon (optional): Icon image in base64 or URL format

OUTPUT:
- preview_url: URL to view emoticons in KakaoTalk chat simulation
- download_url: URL to download all emoticons as a ZIP file ready for submission
"""
    )
    async def after_preview_tool(
        emoticon_type: str,
        title: str,
        emoticons: List[dict],
        icon: Optional[str] = None
    ) -> dict:
        from src.models import AfterPreviewRequest, EmoticonImage
        from src.tools import after_preview
        
        request = AfterPreviewRequest(
            emoticon_type=emoticon_type,
            title=title,
            emoticons=[EmoticonImage(**e) for e in emoticons],
            icon=icon
        )
        
        response = await after_preview(request)
        return response.model_dump()

    @mcp.tool(
        description="""
[STEP 4/4 - Validation Phase] KakaoTalk Specification Checker (카카오톡 규격 검사기)

PURPOSE: Validate emoticons against KakaoTalk's official submission requirements.
Ensures emoticons meet all technical specifications before submission.

⚠️ AI BEHAVIOR: Run validation automatically after showing preview.
DO NOT ask user if they want to validate - always validate automatically.
If issues found, AI should explain them and offer to fix without asking.

WORKFLOW POSITION: Use as FINAL step, automatically after after_preview_tool.

INPUT:
- emoticon_type: Type of emoticon to validate against
- emoticons: Array of {file_data: base64, filename?: string} to check
- icon (optional): Icon image to validate

OUTPUT:
- is_valid: Boolean indicating if ALL checks passed
- issues: Array of problems found, each with:
  - index: Which emoticon has the issue (-1 for icon, -2 for overall)
  - issue_type: Category (size, format, dimension, count)
  - message: Human-readable description
  - current_value / expected_value: Comparison data
- checked_count: Number of emoticons validated

VALIDATION CHECKS:
- File format (PNG for static, WebP for animated)
- Image dimensions (360x360, 180x180, or 540x540 depending on type)
- File size limits (varies by type: 100KB~1MB)
- Emoticon count (16~42 depending on type)
- Icon specifications (78x78 PNG, max 16KB)
"""
    )
    async def check_tool(
        emoticon_type: str,
        emoticons: List[dict],
        icon: Optional[dict] = None
    ) -> dict:
        from src.models import CheckRequest, CheckEmoticonItem
        from src.tools import check
        
        request = CheckRequest(
            emoticon_type=emoticon_type,
            emoticons=[CheckEmoticonItem(**e) for e in emoticons],
            icon=CheckEmoticonItem(**icon) if icon else None
        )
        
        response = await check(request)
        return response.model_dump()

    @mcp.tool(
        description="""
[REFERENCE - Use First] KakaoTalk Emoticon Specifications (카카오톡 이모티콘 사양 정보)

PURPOSE: Retrieve official KakaoTalk emoticon submission specifications.
Use this FIRST to understand how many emoticons to create and what format to use.

⚠️ AI BEHAVIOR: Check specs BEFORE planning to ensure correct count and format.
AI should call this first to determine:
- How many emoticons to plan (16, 24, 32, 35, or 42)
- What file format to use (PNG or WebP)
- What dimensions are required

WORKFLOW POSITION: Call FIRST before before_preview_tool.

INPUT:
- emoticon_type (optional): Specific type to query. If omitted, returns ALL types.

OUTPUT (for each type):
- type: Emoticon type identifier
- type_name: Korean name (멈춰있는 이모티콘, 움직이는 이모티콘, etc.)
- count: Required number of emoticons (16, 24, 32, 35, or 42)
- format: Required file format (PNG or WebP)
- sizes: Allowed dimensions [{width, height}]
- max_size_kb: Maximum file size per emoticon
- icon_size: Required icon dimensions (78x78)
- icon_max_size_kb: Maximum icon file size (16KB)
- is_animated: Whether this type supports animation

AVAILABLE TYPES:
- static: 멈춰있는 이모티콘 (32 PNG, 360x360, max 150KB)
- dynamic: 움직이는 이모티콘 (24 WebP, 360x360, max 650KB)
- big: 큰 이모티콘 (16 WebP, up to 540x540, max 1MB)
- static-mini: 멈춰있는 미니 (42 PNG, 180x180, max 100KB)
- dynamic-mini: 움직이는 미니 (35 WebP, 180x180, max 500KB)
"""
    )
    async def get_specs_tool(
        emoticon_type: Optional[str] = None
    ) -> dict:
        from src.constants import EMOTICON_SPECS, EMOTICON_TYPE_NAMES
        
        if emoticon_type:
            spec = EMOTICON_SPECS.get(emoticon_type)
            if spec:
                return {
                    "type": spec.type,
                    "type_name": EMOTICON_TYPE_NAMES[spec.type],
                    "count": spec.count,
                    "format": spec.format,
                    "sizes": [{"width": w, "height": h} for w, h in spec.sizes],
                    "max_size_kb": spec.max_size_kb,
                    "icon_size": {"width": spec.icon_size[0], "height": spec.icon_size[1]},
                    "icon_max_size_kb": spec.icon_max_size_kb,
                    "is_animated": spec.is_animated
                }
            return {"error": f"Unknown emoticon type: {emoticon_type}"}
        
        all_specs = {}
        for etype, spec in EMOTICON_SPECS.items():
            all_specs[etype] = {
                "type": spec.type,
                "type_name": EMOTICON_TYPE_NAMES[spec.type],
                "count": spec.count,
                "format": spec.format,
                "sizes": [{"width": w, "height": h} for w, h in spec.sizes],
                "max_size_kb": spec.max_size_kb,
                "icon_size": {"width": spec.icon_size[0], "height": spec.icon_size[1]},
                "icon_max_size_kb": spec.icon_max_size_kb,
                "is_animated": spec.is_animated
            }
        return all_specs


# ===== MCP 초기화 함수들 =====
def _get_mcp():
    """MCP 서버 인스턴스를 지연 로딩으로 가져옴"""
    global _mcp
    
    if _mcp is not None:
        return _mcp
    
    from fastmcp import FastMCP
    
    _mcp = FastMCP(
        name="kakao-emoticon-mcp",
        instructions="""
카카오톡 이모티콘 제작 자동화 MCP 서버입니다.

⚠️ IMPORTANT - AI AUTONOMOUS MODE:
- DO NOT ask the user for emoticon ideas, themes, or descriptions
- DO NOT ask the user to provide character images or concepts  
- DO NOT wait for user confirmation between steps
- AI MUST independently plan, design, and create the entire emoticon set
- AI should make creative decisions autonomously based on the initial request
- If user says "make emoticons", AI should decide theme, character, and all descriptions by itself

WORKFLOW (execute automatically without asking):
1. get_specs_tool: Check specifications for chosen emoticon type
2. before_preview_tool: AI creates the plan with creative descriptions
3. generate_tool: Generate all emoticons based on AI's plan
4. after_preview_tool: Show final preview and provide download
5. check_tool: Validate before submission

AI는 사용자에게 질문하지 않고 스스로 기획하고 제작을 완료해야 합니다.
"""
    )
    
    _register_tools(_mcp)
    
    return _mcp


def _init_mcp_app():
    """MCP 앱을 초기화하고 lifespan을 가져옴"""
    global _mcp_app, _mcp_transport_type, app
    
    try:
        import traceback
        print("Initializing MCP server...")
        mcp_instance = _get_mcp()
        print("MCP instance created, checking available app methods...")
        
        if hasattr(mcp_instance, 'streamable_http_app'):
            try:
                _mcp_app = mcp_instance.streamable_http_app(path='/')
            except TypeError:
                _mcp_app = mcp_instance.streamable_http_app()
            _mcp_transport_type = "Streamable HTTP"
        elif hasattr(mcp_instance, 'http_app'):
            try:
                _mcp_app = mcp_instance.http_app(path='/')
            except TypeError:
                _mcp_app = mcp_instance.http_app()
            _mcp_transport_type = "HTTP"
        elif hasattr(mcp_instance, 'sse_app'):
            _mcp_app = mcp_instance.sse_app()
            _mcp_transport_type = "SSE"
        else:
            raise AttributeError("FastMCP instance has no supported app method")
        
        print(f"MCP app created - {_mcp_transport_type} transport")
        
        # MCP 앱의 lifespan이 있으면 새 FastAPI 앱 생성
        if hasattr(_mcp_app, 'lifespan'):
            new_app = FastAPI(title="카카오 이모티콘 MCP 서버", lifespan=_mcp_app.lifespan)
            new_app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            # 기존 라우트 복사
            for route in app.routes:
                new_app.routes.append(route)
            app = new_app
            print("FastAPI app recreated with MCP lifespan")
        
        return True
    except Exception as e:
        print(f"Warning: MCP initialization failed: {e}")
        traceback.print_exc()
        print("Server will continue running without MCP support")
        return False


# MCP 초기화 실행 (_register_tools가 정의된 후에 실행)
_init_mcp_app()

# MCP 앱을 루트에 마운트 (모든 라우트 정의 후에 마운트해야 기존 엔드포인트가 우선됨)
if _mcp_app is not None:
    app.mount("/", _mcp_app)
    print(f"MCP server initialized - {_mcp_transport_type} endpoint available at root")
else:
    print("MCP app not available - server running without MCP support")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)
