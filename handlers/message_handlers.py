import random
from telethon import events

async def message_event(event: events.NewMessage.Event):
    # Ensure the message and its text exist
    if not event.message or not event.message.text:
        return

    text = event.message.text

    # تثبيحات
    if text.startswith("ثبح ") or text == "ثبح":
        await event.reply("ثباحو")
    elif text.startswith("ثباحو ") or text == "ثباحو":
        await event.reply("ثبح")
    elif text.startswith("مثائو ") or text == "مثائو":
        await event.reply("مثا")
    elif text.startswith("مثا ") or text == "مثا":
        await event.reply("مثائو")

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
            sender = await event.get_sender()
            if sender and sender.username == "Shinobi7k":
                if "ابوك" in text:
                    await event.reply(random.choice(father))
                    return

        # shinobi responses
        for word in shinobi_keywords:
            if word in text:
                if "ابوك" in text:
                    await event.reply(random.choice(father))
                    return
                if "بيعذبك" in text:
                    await event.reply(random.choice(azab))
                    return
                if "بتطبل" in text:
                    await event.reply(random.choice(tabla))
                    return

        # steins responses
        for word in steins_keys:
            if word in text:
                await event.reply(random.choice(steins))
                return

        # exceptions
        if "هكسب" in text:
            await event.reply(random.choice(win))
            return
        if "حبك" in text or "حبق" in text:
            await event.reply(random.choice(love))
            return
        if "عامل ايه" in text or "عامل إيه" in text or "كيف حالك" in text:
            await event.reply(random.choice(elhal))
            return

        # normal responses
        if " " in text:
            await event.reply(random.choice(normal_responses))
        else:
            await event.reply(random.choice(hellos))
