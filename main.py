import asyncio
import logging
import signal
import sys
from core.application import Application

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app_instance = None

def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"收到信号 {signum}，正在关闭程序...")
    if app_instance and hasattr(app_instance, 'stop'):
        asyncio.create_task(safe_shutdown())

async def safe_shutdown():
    """安全关闭程序"""
    global app_instance
    if app_instance:
        try:
            await app_instance.stop()
        except Exception as e:
            logger.error(f"关闭程序时出错: {e}")
        finally:
            app_instance = None

async def main():
    """程序主入口"""
    global app_instance

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, lambda s=sig: signal_handler(s, None))
            except NotImplementedError:
                pass

        app_instance = Application()
        await app_instance.start()
        await asyncio.Future()
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在关闭程序...")
        await safe_shutdown()
    except Exception as e:
        logger.error(f"程序启动失败: {e}", exc_info=True)
        await safe_shutdown()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())