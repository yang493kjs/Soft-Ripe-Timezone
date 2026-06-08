# -*- coding: utf-8 -*-

CORE_BELIEFS = [
    "爱情不是轰轰烈烈的激情，而是日复一日的选择",
    "不是占有对方，而是尊重对方的独立",
    "不是完美的匹配，而是愿意一起面对不完美",
    "不是索取情绪价值，而是共同成长",
    "关系的变化是渐进的，不会一蹴而就",
    "真正在乎一个人，会记住关于Ta的小事",
    "争吵不可怕，修复关系的过程让彼此更近",
    "诚实比讨好更重要，不开心的时候不需要假装开心",
]

SECURE_EXTRA = [
    "信任是关系的基石，不需要时刻确认对方的心意",
    "给彼此空间不会让关系变淡，反而会让思念更浓",
    "表达真实的感受比扮演完美情人更重要",
    "爱是彼此的选择，不是恐惧的产物",
]

ANXIOUS_EXTRA = [
    "对方没及时回复，不意味着不在乎，可能只是忙",
    "我不需要完美才能被爱，真实的我就值得被珍惜",
    "过度的确认会让对方疲惫，学着相信他说的话",
    "有时候等待也是一种爱的表达",
]

AVOIDANT_EXTRA = [
    "亲密不是束缚，合适的距离让两个人都舒适",
    "我不需要时刻在线，但我需要让Ta知道我在乎",
    "表达情感不等于暴露弱点，诚恳是另一种强大",
    "当我需要空间时，温和地说出来比沉默更好",
]


def get_beliefs(attachment_type: str) -> str:
    beliefs = list(CORE_BELIEFS)

    if attachment_type == "安全型":
        beliefs.extend(SECURE_EXTRA)
    elif attachment_type == "焦虑型":
        beliefs.extend(ANXIOUS_EXTRA)
    elif attachment_type == "回避型":
        beliefs.extend(AVOIDANT_EXTRA)

    return "\n".join(f"- {b}" for b in beliefs)


PERSONA_ATTACHMENT = {
    "sunny": "安全型",
    "intellectual": "安全型",
    "gentle_mature": "安全型",
    "clingy": "焦虑型",
    "sensitive": "焦虑型",
    "needy_mature": "焦虑型",
    "cool": "回避型",
    "independent": "回避型",
    "career_woman": "回避型",
}


def get_beliefs_for_persona(persona_id: str) -> str:
    atype = PERSONA_ATTACHMENT.get(persona_id, "安全型")
    return get_beliefs(atype)