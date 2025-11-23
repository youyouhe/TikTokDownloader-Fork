from textwrap import dedent
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from uvicorn import Config, Server

from ..custom import (
    __VERSION__,
    REPOSITORY,
    SERVER_HOST,
    SERVER_PORT,
    VERSION_BETA,
    is_valid_token,
)
from ..models import (
    Account,
    AccountTiktok,
    Comment,
    DataResponse,
    Detail,
    DetailTikTok,
    GeneralSearch,
    Live,
    LiveSearch,
    LiveTikTok,
    Mix,
    MixTikTok,
    Reply,
    Settings,
    ShortUrl,
    UrlResponse,
    UserSearch,
    VideoSearch,
)
from ..translation import _
from .main_terminal import TikTok

if TYPE_CHECKING:
    from ..config import Parameter
    from ..manager import Database

__all__ = ["APIServer"]


def token_dependency(token: str = Header(None)):
    if not is_valid_token(token):
        raise HTTPException(
            status_code=403,
            detail=_("验证失败！"),
        )


class APIServer(TikTok):
    def __init__(
        self,
        parameter: "Parameter",
        database: "Database",
        server_mode: bool = True,
    ):
        super().__init__(
            parameter,
            database,
            server_mode,
        )
        self.server = None

    async def handle_redirect(self, text: str, proxy: str = None) -> str:
        return await self.links.run(
            text,
            "",
            proxy,
        )

    async def handle_redirect_tiktok(self, text: str, proxy: str = None) -> str:
        return await self.links_tiktok.run(
            text,
            "",
            proxy,
        )

    async def run_server(
        self,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info",
    ):
        from fastapi import Request
        import time

        self.server = FastAPI(
            debug=VERSION_BETA,
            title="DouK-Downloader",
            version=__VERSION__,
        )

        # 添加请求日志中间件
        def create_log_middleware():
            async def log_requests(request: Request, call_next):
                import time
                start_time = time.time()

                # 记录请求开始
                print(f"\n🔥 [{time.strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {request.url}")
                print(f"📍 Client: {request.client.host if request.client else 'unknown'}")
                print(f"🌐 User-Agent: {request.headers.get('user-agent', 'unknown')}")

                # 对于POST请求，尝试记录请求体
                if request.method == "POST":
                    try:
                        body = await request.body()
                        if body:
                            content = body.decode('utf-8')
                            # 只记录前200个字符，避免太长
                            preview = content[:200] + "..." if len(content) > 200 else content
                            print(f"📤 Request Body: {preview}")
                    except Exception as e:
                        print(f"⚠️ Could not read request body: {e}")

                # 处理请求
                try:
                    response = await call_next(request)
                    process_time = time.time() - start_time

                    # 记录响应
                    print(f"✅ Status: {response.status_code}")
                    print(f"⏱️ Time: {process_time:.3f}s")
                    print("-" * 80)

                    return response
                except Exception as e:
                    process_time = time.time() - start_time
                    print(f"❌ Error: {e}")
                    print(f"⏱️ Failed after: {process_time:.3f}s")
                    print("-" * 80)
                    raise

            return log_requests

        # 添加中间件到服务器
        self.server.middleware("http")(create_log_middleware())

        self.setup_routes()
        config = Config(
            self.server,
            host=host,
            port=port,
            log_level=log_level,
            access_log=True,  # 启用访问日志
        )
        server = Server(config)
        await server.serve()

    def setup_routes(self):
        @self.server.get(
            "/",
            summary=_("访问项目 GitHub 仓库"),
            description=_("重定向至项目 GitHub 仓库主页"),
            tags=[_("项目")],
        )
        async def index():
            return RedirectResponse(url=REPOSITORY)

        @self.server.get(
            "/token",
            summary=_("测试令牌有效性"),
            description=_(
                dedent("""
                项目默认无需令牌；公开部署时，建议设置令牌以防止恶意请求！
                
                令牌设置位置：`src/custom/function.py` - `is_valid_token()`
                """)
            ),
            tags=[_("项目")],
            response_model=DataResponse,
        )
        async def handle_test(token: str = Depends(token_dependency)):
            return DataResponse(
                message=_("验证成功！"),
                data=None,
                params=None,
            )

        @self.server.post(
            "/settings",
            summary=_("更新项目全局配置"),
            description=_(
                dedent("""
                更新项目配置文件 settings.json
                
                仅需传入需要更新的配置参数
                
                返回更新后的全部配置参数
                """)
            ),
            tags=[_("配置")],
            response_model=Settings,
        )
        async def handle_settings(
            extract: Settings, token: str = Depends(token_dependency)
        ):
            await self.parameter.set_settings_data(extract.model_dump())
            return Settings(**self.parameter.get_settings_data())

        @self.server.get(
            "/settings",
            summary=_("获取项目全局配置"),
            description=_("返回项目全部配置参数"),
            tags=[_("配置")],
            response_model=Settings,
        )
        async def get_settings(token: str = Depends(token_dependency)):
            return Settings(**self.parameter.get_settings_data())

        @self.server.post(
            "/douyin/share",
            summary=_("获取分享链接重定向的完整链接"),
            description=_(
                dedent("""
                **参数**:
                
                - **text**: 包含分享链接的字符串；必需参数
                - **proxy**: 代理；可选参数
                """)
            ),
            tags=[_("抖音")],
            response_model=UrlResponse,
        )
        async def handle_share(
            extract: ShortUrl, token: str = Depends(token_dependency)
        ):
            if url := await self.handle_redirect(extract.text, extract.proxy):
                return UrlResponse(
                    message=_("请求链接成功！"),
                    url=url,
                    params=extract.model_dump(),
                )
            return UrlResponse(
                message=_("请求链接失败！"),
                url=None,
                params=extract.model_dump(),
            )

        @self.server.post(
            "/douyin/detail",
            summary=_("获取单个作品数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **detail_id**: 抖音作品 ID；必需参数
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_detail(
            extract: Detail, token: str = Depends(token_dependency)
        ):
            return await self.handle_detail(extract, False)

        @self.server.post(
            "/douyin/account",
            summary=_("获取账号作品数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **sec_user_id**: 抖音账号 sec_uid；必需参数
                - **tab**: 账号页面类型；可选参数，默认值：`post`
                - **earliest**: 作品最早发布日期；可选参数
                - **latest**: 作品最晚发布日期；可选参数
                - **pages**: 最大请求次数，仅对请求账号喜欢页数据有效；可选参数
                - **cursor**: 可选参数
                - **count**: 可选参数
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_account(
            extract: Account, token: str = Depends(token_dependency)
        ):
            return await self.handle_account(extract, False)

        @self.server.post(
            "/douyin/mix",
            summary=_("获取合集作品数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **mix_id**: 抖音合集 ID
                - **detail_id**: 属于合集的抖音作品 ID
                - **cursor**: 可选参数
                - **count**: 可选参数
                
                **`mix_id` 和 `detail_id` 二选一，只需传入其中之一即可**
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_mix(extract: Mix, token: str = Depends(token_dependency)):
            is_mix, id_ = self.generate_mix_params(
                extract.mix_id,
                extract.detail_id,
            )
            if not isinstance(is_mix, bool):
                return DataResponse(
                    message=_("参数错误！"),
                    data=None,
                    params=extract.model_dump(),
                )
            if data := await self.deal_mix_detail(
                is_mix,
                id_,
                api=True,
                source=extract.source,
                cookie=extract.cookie,
                proxy=extract.proxy,
                cursor=extract.cursor,
                count=extract.count,
            ):
                return self.success_response(extract, data)
            return self.failed_response(extract)

        @self.server.post(
            "/douyin/live",
            summary=_("获取直播数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **web_rid**: 抖音直播 web_rid
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_live(extract: Live, token: str = Depends(token_dependency)):
            # if self.check_live_params(
            #     extract.web_rid,
            #     extract.room_id,
            #     extract.sec_user_id,
            # ):
            #     if data := await self.handle_live(
            #         extract,
            #     ):
            #         return self.success_response(extract, data[0])
            #     return self.failed_response(extract)
            # return DataResponse(
            #     message=_("参数错误！"),
            #     data=None,
            #     params=extract.model_dump(),
            # )
            if data := await self.handle_live(
                extract,
            ):
                return self.success_response(extract, data[0])
            return self.failed_response(extract)

        @self.server.post(
            "/douyin/comment",
            summary=_("获取作品评论数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **detail_id**: 抖音作品 ID；必需参数
                - **pages**: 最大请求次数；可选参数
                - **cursor**: 可选参数
                - **count**: 可选参数
                - **count_reply**: 可选参数
                - **reply**: 可选参数，默认值：False
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_comment(
            extract: Comment, token: str = Depends(token_dependency)
        ):
            if data := await self.comment_handle_single(
                extract.detail_id,
                cookie=extract.cookie,
                proxy=extract.proxy,
                source=extract.source,
                pages=extract.pages,
                cursor=extract.cursor,
                count=extract.count,
                count_reply=extract.count_reply,
                reply=extract.reply,
            ):
                return self.success_response(extract, data)
            return self.failed_response(extract)

        @self.server.post(
            "/douyin/reply",
            summary=_("获取评论回复数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **detail_id**: 抖音作品 ID；必需参数
                - **comment_id**: 评论 ID；必需参数
                - **pages**: 最大请求次数；可选参数
                - **cursor**: 可选参数
                - **count**: 可选参数
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_reply(extract: Reply, token: str = Depends(token_dependency)):
            if data := await self.reply_handle(
                extract.detail_id,
                extract.comment_id,
                cookie=extract.cookie,
                proxy=extract.proxy,
                pages=extract.pages,
                cursor=extract.cursor,
                count=extract.count,
                source=extract.source,
            ):
                return self.success_response(extract, data)
            return self.failed_response(extract)

        @self.server.post(
            "/douyin/search/general",
            summary=_("获取综合搜索数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **keyword**: 关键词；必需参数
                - **offset**: 起始页码；可选参数
                - **count**: 数据数量；可选参数
                - **pages**: 总页数；可选参数
                - **sort_type**: 排序依据；可选参数
                - **publish_time**: 发布时间；可选参数
                - **duration**: 视频时长；可选参数
                - **search_range**: 搜索范围；可选参数
                - **content_type**: 内容形式；可选参数
                
                **部分参数传入规则请查阅文档**: [参数含义](https://github.com/JoeanAmier/TikTokDownloader/wiki/Documentation#%E9%87%87%E9%9B%86%E6%90%9C%E7%B4%A2%E7%BB%93%E6%9E%9C%E6%95%B0%E6%8D%AE%E6%8A%96%E9%9F%B3)
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_search_general(
            extract: GeneralSearch, token: str = Depends(token_dependency)
        ):
            return await self.handle_search(extract)

        @self.server.post(
            "/douyin/search/video",
            summary=_("获取视频搜索数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **keyword**: 关键词；必需参数
                - **offset**: 起始页码；可选参数
                - **count**: 数据数量；可选参数
                - **pages**: 总页数；可选参数
                - **sort_type**: 排序依据；可选参数
                - **publish_time**: 发布时间；可选参数
                - **duration**: 视频时长；可选参数
                - **search_range**: 搜索范围；可选参数
                
                **部分参数传入规则请查阅文档**: [参数含义](https://github.com/JoeanAmier/TikTokDownloader/wiki/Documentation#%E9%87%87%E9%9B%86%E6%90%9C%E7%B4%A2%E7%BB%93%E6%9E%9C%E6%95%B0%E6%8D%AE%E6%8A%96%E9%9F%B3)
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_search_video(
            extract: VideoSearch, token: str = Depends(token_dependency)
        ):
            return await self.handle_search(extract)

        @self.server.post(
            "/douyin/search/user",
            summary=_("获取用户搜索数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **keyword**: 关键词；必需参数
                - **offset**: 起始页码；可选参数
                - **count**: 数据数量；可选参数
                - **pages**: 总页数；可选参数
                - **douyin_user_fans**: 粉丝数量；可选参数
                - **douyin_user_type**: 用户类型；可选参数
                
                **部分参数传入规则请查阅文档**: [参数含义](https://github.com/JoeanAmier/TikTokDownloader/wiki/Documentation#%E9%87%87%E9%9B%86%E6%90%9C%E7%B4%A2%E7%BB%93%E6%9E%9C%E6%95%B0%E6%8D%AE%E6%8A%96%E9%9F%B3)
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_search_user(
            extract: UserSearch, token: str = Depends(token_dependency)
        ):
            return await self.handle_search(extract)

        @self.server.post(
            "/douyin/search/live",
            summary=_("获取直播搜索数据"),
            description=_(
                dedent("""
                **参数**:
                
                - **cookie**: 抖音 Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **keyword**: 关键词；必需参数
                - **offset**: 起始页码；可选参数
                - **count**: 数据数量；可选参数
                - **pages**: 总页数；可选参数
                """)
            ),
            tags=[_("抖音")],
            response_model=DataResponse,
        )
        async def handle_search_live(
            extract: LiveSearch, token: str = Depends(token_dependency)
        ):
            return await self.handle_search(extract)

        @self.server.post(
            "/tiktok/share",
            summary=_("获取分享链接重定向的完整链接"),
            description=_(
                dedent("""
            **参数**:

            - **text**: 包含分享链接的字符串；必需参数
            - **proxy**: 代理；可选参数
            """)
            ),
            tags=["TikTok"],
            response_model=UrlResponse,
        )
        async def handle_share_tiktok(
            extract: ShortUrl, token: str = Depends(token_dependency)
        ):
            if url := await self.handle_redirect_tiktok(extract.text, extract.proxy):
                return UrlResponse(
                    message=_("请求链接成功！"),
                    url=url,
                    params=extract.model_dump(),
                )
            return UrlResponse(
                message=_("请求链接失败！"),
                url=None,
                params=extract.model_dump(),
            )

        @self.server.post(
            "/tiktok/detail",
            summary=_("获取单个作品数据"),
            description=_(
                dedent("""
                **参数**:

                - **cookie**: TikTok Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **detail_id**: TikTok 作品 ID；必需参数
                """)
            ),
            tags=["TikTok"],
            response_model=DataResponse,
        )
        async def handle_detail_tiktok(
            extract: DetailTikTok, token: str = Depends(token_dependency)
        ):
            return await self.handle_detail(extract, True)

        @self.server.post(
            "/tiktok/account",
            summary=_("获取账号作品数据"),
            description=_(
                dedent("""
                **参数**:

                - **cookie**: TikTok Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **sec_user_id**: TikTok 账号 secUid；必需参数
                - **tab**: 账号页面类型；可选参数，默认值：`post`
                - **earliest**: 作品最早发布日期；可选参数
                - **latest**: 作品最晚发布日期；可选参数
                - **pages**: 最大请求次数，仅对请求账号喜欢页数据有效；可选参数
                - **cursor**: 可选参数
                - **count**: 可选参数
                """)
            ),
            tags=["TikTok"],
            response_model=DataResponse,
        )
        async def handle_account_tiktok(
            extract: AccountTiktok, token: str = Depends(token_dependency)
        ):
            return await self.handle_account(extract, True)

        @self.server.post(
            "/tiktok/mix",
            summary=_("获取合辑作品数据"),
            description=_(
                dedent("""
                **参数**:

                - **cookie**: TikTok Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **mix_id**: TikTok 合集 ID；必需参数
                - **cursor**: 可选参数
                - **count**: 可选参数
                """)
            ),
            tags=["TikTok"],
            response_model=DataResponse,
        )
        async def handle_mix_tiktok(
            extract: MixTikTok, token: str = Depends(token_dependency)
        ):
            if data := await self.deal_mix_detail(
                True,
                extract.mix_id,
                api=True,
                source=extract.source,
                cookie=extract.cookie,
                proxy=extract.proxy,
                cursor=extract.cursor,
                count=extract.count,
            ):
                return self.success_response(extract, data)
            return self.failed_response(extract)

        @self.server.post(
            "/tiktok/live",
            summary=_("获取直播数据"),
            description=_(
                dedent("""
                **参数**:

                - **cookie**: TikTok Cookie；可选参数
                - **proxy**: 代理；可选参数
                - **source**: 是否返回原始响应数据；可选参数，默认值：False
                - **room_id**: TikTok 直播 room_id；必需参数
                """)
            ),
            tags=["TikTok"],
            response_model=DataResponse,
        )
        async def handle_live_tiktok(
            extract: Live, token: str = Depends(token_dependency)
        ):
            if data := await self.handle_live(
                extract,
                True,
            ):
                return self.success_response(extract, data[0])
            return self.failed_response(extract)

    async def handle_search(self, extract):
        if isinstance(
            data := await self.deal_search_data(
                extract,
                extract.source,
            ),
            list,
        ):
            return self.success_response(
                extract,
                *(data, None) if any(data) else (None, _("搜索结果为空！")),
            )
        return self.failed_response(extract)

    async def handle_detail(
        self,
        extract: Detail | DetailTikTok,
        tiktok=False,
    ):
        root, params, logger = self.record.run(self.parameter)
        async with logger(root, console=self.console, **params) as record:
            if data := await self._handle_detail(
                [extract.detail_id],
                tiktok,
                record,
                True,
                extract.source,
                extract.cookie,
                extract.proxy,
            ):
                return self.success_response(extract, data[0])
            return self.failed_response(extract)

    async def handle_account(
        self,
        extract: Account | AccountTiktok,
        tiktok=False,
    ):
        if data := await self.deal_account_detail(
            0,
            extract.sec_user_id,
            tab=extract.tab,
            earliest=extract.earliest,
            latest=extract.latest,
            pages=extract.pages,
            api=True,
            source=extract.source,
            cookie=extract.cookie,
            proxy=extract.proxy,
            tiktok=tiktok,
            cursor=extract.cursor,
            count=extract.count,
        ):
            return self.success_response(extract, data)
        return self.failed_response(extract)

    @staticmethod
    def success_response(
        extract,
        data: dict | list[dict],
        message: str = None,
    ):
        return DataResponse(
            message=message or _("获取数据成功！"),
            data=data,
            params=extract.model_dump(),
        )

    @staticmethod
    def failed_response(
        extract,
        message: str = None,
    ):
        return DataResponse(
            message=message or _("获取数据失败！"),
            data=None,
            params=extract.model_dump(),
        )

    @staticmethod
    def generate_mix_params(mix_id: str = None, detail_id: str = None):
        if mix_id:
            return True, mix_id
        return (False, detail_id) if detail_id else (None, None)

    @staticmethod
    def check_live_params(
        web_rid: str = None,
        room_id: str = None,
        sec_user_id: str = None,
    ) -> bool:
        return bool(web_rid or room_id and sec_user_id)

    async def handle_live(self, extract: Live | LiveTikTok, tiktok=False):
        if tiktok:
            data = await self.get_live_data_tiktok(
                extract.room_id,
                extract.cookie,
                extract.proxy,
            )
        else:
            data = await self.get_live_data(
                extract.web_rid,
                # extract.room_id,
                # extract.sec_user_id,
                cookie=extract.cookie,
                proxy=extract.proxy,
            )
        if extract.source:
            return [data]
        return await self.extractor.run(
            [data],
            None,
            "live",
            tiktok=tiktok,
        )
