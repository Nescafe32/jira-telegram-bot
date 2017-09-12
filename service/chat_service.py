from model.chat import Chat
from model.user import User
from model.permission import Permission
from telegram.ext import JobQueue
from telegram import ParseMode
from service import jira_service
from config import JIRA_REQUESTS_SECONDS_PERIOD


def init_bot(job_queue: JobQueue):
    for chat in Chat.select(Chat):
        add_job(job_queue, chat)


def help_command(bot, update):
    bot.send_message(text="Use next commands to work with bot:" + "\n" +
                          "/set <username>  - to setup user who's issues you want to get",
                     chat_id=update.message.chat_id)


def set_user(bot, update, args, job_queue: JobQueue, chat_data):
    if update.message.from_user.id not in [p.t_id for p in Permission.select(Permission.t_id)]:
        update.message.reply_text("You don't have permission to get issues from this jira-service")
        return

    user = User.get_or_create(name=args[0])[0]

    t_id = update.message.chat_id

    chats = Chat.select().where(Chat.t_id == t_id)
    if len(chats) > 0:
        chat = chats[0]
        chat.user = user
        chat.save()
    else:
        chat = Chat.create(t_id=t_id, user=user)

    jira_service.init_user_issues(user)

    add_job(job_queue, chat)

    update.message.reply_text('You will get issues notifications from user: ' + user.name)


def send_issue(bot, job):
    chat = job.context
    for issue in jira_service.get_new_issues(username=chat.user.name):
        bot.send_message(chat_id=chat.t_id, text=issue.__str__(), parse_mode=ParseMode.MARKDOWN)


def add_job(job_queue: JobQueue, chat: Chat):
    jobs = job_queue.jobs()
    for job in [job for job in jobs if job.context.id == chat.id]:
        job.enabled = False
        job.schedule_removal()

    job_queue.run_repeating(send_issue, int(JIRA_REQUESTS_SECONDS_PERIOD), context=chat)
