"""CornerCheck Slack app entrypoint (Socket Mode + a health/landing HTTP server)."""

import logging
import os

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from cornercheck.app.actions import register_actions
from cornercheck.app.assistant import assistant
from cornercheck.app.home import register_home
from cornercheck.app.mentions import register_mentions
from cornercheck.app.workflow_step import register_workflow_step
from cornercheck.config import get_settings

log = logging.getLogger("cornercheck.app")


def build_app() -> App:
    settings = get_settings()
    app = App(token=settings.slack_bot_token)
    app.use(assistant)
    register_actions(app)
    register_home(app)
    register_mentions(app)
    register_workflow_step(app)

    @app.error
    def on_unhandled_error(error: Exception, body: dict) -> None:
        # Last-resort net: Bolt's default handler only logs. Individual handlers post
        # their own fail-closed replies; this catches anything they miss.
        log.exception("unhandled listener error: %s", body.get("type"))

    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()

    # Bind the health/landing server FIRST so Render sees an open port immediately (only
    # when $PORT is set; local runs stay Socket-Mode-only).
    port = os.environ.get("PORT")
    if port:
        from cornercheck.app.web import start_health_server

        start_health_server(int(port))
        from cornercheck.bootstrap import bootstrap_db

        bootstrap_db()  # self-provision the deployed DB on first boot

    # Proactive roster monitor: deterministic daily digest (window math + ledger diffs).
    # Independent of Slack tokens (webhook push), so it starts in every mode.
    from cornercheck.monitor import start_monitor_thread

    start_monitor_thread()

    # Degrade gracefully if Slack secrets aren't set yet: the landing URL stays up while the
    # operator adds tokens in the dashboard, instead of crash-looping the deploy.
    if not (settings.slack_bot_token and settings.slack_app_token):
        log.warning(
            "Slack tokens not set; running health/landing only. Add them to start the agent."
        )
        if port:
            import time

            while True:
                time.sleep(3600)
        return

    app = build_app()
    log.info("CornerCheck starting (Socket Mode, model=%s)", settings.cornercheck_model)
    SocketModeHandler(app, settings.slack_app_token).start()


if __name__ == "__main__":
    main()
