import dramatiq
from dramatiq.brokers.redis import RedisBroker

from fencing_api.config import get_settings

broker = RedisBroker(url=get_settings().redis_url)
dramatiq.set_broker(broker)


@dramatiq.actor(queue_name="video", max_retries=2, time_limit=1_800_000)
def process_video_task(video_id: str) -> None:
    from fencing_api.services.video_jobs import run_video_job

    run_video_job(video_id)
