from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import random


# Message events
async def message_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ensure the message and its text exist
    if update.message is None or update.message.text is None:
        return

    text = update.message.text

    # تثبيحات
    if text.startswith("ثبح ") or text == "ثبح":
        await update.message.reply_text("ثباحو")
    elif text.startswith("ثباحو ") or text == "ثباحو":
        await update.message.reply_text("ثبح")
    elif text.startswith("مثائو ") or text == "مثائو":
        await update.message.reply_text("مثا")
    elif text.startswith("مثا ") or text == "مثا":
        await update.message.reply_text("مثائو")

    # يالبوت
    if "يالبوت" in text:
        normal_responses = [
            "اكيد يسطا", "اكيد يبرو", "بدون شك", "يب اكيد", "طبعا", "اومال", "ايوه",
            "يب", "يب يب", "اتكل علي الله يعم", "مش فايقلك",
            "هي دي محتاجه سؤال!؟", "لا", "انا بقولك لا", "اكيد لا", "نوب", "معرفش",
            "اكيد يغالي", "اكيد ينقم", "لا هه", "صدقني انا ذات نفسي معرفش", "انا لو أعرف هقولك"
        ]
        hellos = ["نعم", "نعم يغالي", "نعم ينقم", "عايز ايه", "نعم يخويا"]
        steins_keys = ["stein", "شتاين", "ستاين"]
        steins = [
            "شتاينز الأعظم", "شتاينز فوق", "شتاينز فوق مستوي التقييم البشري", "شتاينز اعظم انمي"
        ]
        shinobi_keywords = ["shinobi", "شنوبي", "شنبي", "شنوب", "شينوبي"]
        father = [
            "شنوبي ابويا وعمي وعم عيالي", "شنبي ابويا وعمي", "شنوبي احسن اب في العالم"
        ]
        azab = [
            "ده حنين عليا خالث", "بابا شنبي مش بيمد ايده عليا", "مش بيلمسني"
        ]
        tabla = [
            "لا طبعا يغالي", "شنوبي عمي وعم عيالي", "شنوبي عمك", "شنوبي فوق"
        ]
        love = ["حبك", "حبق", "وانا كمان يغالي", "+1"]
        win = ["مش هتكسب هه", "نصيبك مش هتكسب", "انا بقولك لا", "على ضمانتي"]
        elhal = ["الحمدلله يخويا", "الحمدلله يغالي", "تمام الحمدلله"]

        # me responses
        if "انا" in text:
            if update.message.from_user and update.message.from_user.username == "Shinobi7k":
                if "ابوك" in text:
                    await update.message.reply_text(random.choice(father))
                    return

        # shinobi responses
        for word in shinobi_keywords:
            if word in text:
                if "ابوك" in text:
                    await update.message.reply_text(random.choice(father))
                    return
                if "بيعذبك" in text:
                    await update.message.reply_text(random.choice(azab))
                    return
                if "بتطبل" in text:
                    await update.message.reply_text(random.choice(tabla))
                    return

        # steins responses
        for word in steins_keys:
            if word in text:
                await update.message.reply_text(random.choice(steins))
                return

        # exceptions
        if "هكسب" in text:
            await update.message.reply_text(random.choice(win))
            return
        if "حبك" in text or "حبق" in text:
            await update.message.reply_text(random.choice(love))
            return
        if "عامل ايه" in text or "عامل إيه" in text or "كيف حالك" in text:
            await update.message.reply_text(random.choice(elhal))
            return

        # normal responses
        if " " in text:
            await update.message.reply_text(random.choice(normal_responses))
        else:
            await update.message.reply_text(random.choice(hellos))