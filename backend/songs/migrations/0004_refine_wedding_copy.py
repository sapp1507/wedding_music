from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import migrations


def upsert_by_order(model, page, order, defaults):
    item = model.objects.filter(page=page, order=order).order_by("id").first()
    if item:
        for field, value in defaults.items():
            setattr(item, field, value)
        item.save()
        return item
    return model.objects.create(page=page, order=order, **defaults)


def refine_wedding_copy(apps, schema_editor):
    WeddingPage = apps.get_model("songs", "WeddingPage")
    WeddingEvent = apps.get_model("songs", "WeddingEvent")
    WeddingFAQ = apps.get_model("songs", "WeddingFAQ")
    WeddingInfoBlock = apps.get_model("songs", "WeddingInfoBlock")

    page = WeddingPage.objects.filter(
        groom_name="Алексей",
        bride_name="Мария",
    ).order_by("id").first()
    if not page:
        return

    tz = ZoneInfo("Europe/Moscow")
    page.wedding_date = datetime(2026, 9, 4, 14, 45, tzinfo=tz)
    page.hero_kicker = "4 сентября 2026"
    page.invitation_text = (
        "В нашей жизни скоро состоится важное событие - наша свадьба. "
        "Мы будем рады разделить этот день с вами и провести его в кругу "
        "самых близких людей."
    )
    page.location_title = "Обновление по месту проведения"
    page.location_name = 'Парк-отель "Жемчужина"'
    page.location_address = "г. Владимир, Южное шоссе, 23"
    page.location_map_url = "https://yandex.ru/maps/-/CTRArMpi"
    page.footer_title = "Будем рады видеть вас на нашем празднике!"
    page.footer_text = "Спасибо, что разделите с нами этот важный день."
    page.save()

    event_defaults = [
        (
            1,
            {
                "title": "Сбор гостей",
                "description": "ЗАГС г. Владимир, ул. Растопчина, 51",
                "starts_at": datetime(2026, 9, 4, 14, 20, tzinfo=tz),
                "is_visible": True,
            },
        ),
        (
            2,
            {
                "title": "Церемония регистрации",
                "description": "ЗАГС г. Владимир, ул. Растопчина, 51",
                "starts_at": datetime(2026, 9, 4, 14, 45, tzinfo=tz),
                "is_visible": True,
            },
        ),
        (
            3,
            {
                "title": "Фотосессия жениха и невесты",
                "description": 'Парк-отель "Жемчужина", г. Владимир, Южное шоссе, 23',
                "starts_at": datetime(2026, 9, 4, 16, 0, tzinfo=tz),
                "is_visible": True,
            },
        ),
        (
            4,
            {
                "title": "Фуршет",
                "description": 'Парк-отель "Жемчужина", г. Владимир, Южное шоссе, 23',
                "starts_at": datetime(2026, 9, 4, 16, 0, tzinfo=tz),
                "is_visible": True,
            },
        ),
        (
            5,
            {
                "title": "Праздничный банкет",
                "description": 'Ресторан "Гурман", парк-отель "Жемчужина"',
                "starts_at": datetime(2026, 9, 4, 17, 30, tzinfo=tz),
                "is_visible": True,
            },
        ),
        (
            6,
            {
                "title": "Завершение вечера",
                "description": "",
                "starts_at": datetime(2026, 9, 4, 23, 0, tzinfo=tz),
                "is_visible": True,
            },
        ),
    ]
    for order, defaults in event_defaults:
        upsert_by_order(WeddingEvent, page, order, defaults)
    WeddingEvent.objects.filter(page=page, order__gt=6).update(is_visible=False)

    info_defaults = [
        (
            1,
            {
                "title": "Новое место проведения",
                "body": (
                    "В связи с увеличением количества гостей место проведения "
                    'праздничной части изменено. Мероприятие состоится в парк-отеле "Жемчужина".'
                ),
                "link_label": "",
                "link_url": "",
                "is_visible": True,
            },
        ),
        (
            2,
            {
                "title": "Регистрация",
                "body": (
                    "На торжественной регистрации брака могут присутствовать все желающие гости."
                ),
                "link_label": "",
                "link_url": "",
                "is_visible": True,
            },
        ),
        (
            3,
            {
                "title": "Проживание",
                "body": (
                    'В парк-отеле "Жемчужина" можно заранее забронировать номера, '
                    "а также дом для размещения до 6 гостей. Подробная информация доступна на сайте отеля."
                ),
                "link_label": 'Парк-отель "Жемчужина"',
                "link_url": "https://www.perlotel.ru/",
                "is_visible": True,
            },
        ),
    ]
    for order, defaults in info_defaults:
        upsert_by_order(WeddingInfoBlock, page, order, defaults)
    WeddingInfoBlock.objects.filter(page=page, order__gt=3).update(is_visible=False)

    faq_defaults = [
        (
            1,
            {
                "question": "Где могут остановиться гости из других городов?",
                "answer": (
                    'Банкет пройдет в парк-отеле "Жемчужина". При необходимости '
                    "вы можете заранее забронировать номер на сайте отеля: https://www.perlotel.ru/"
                ),
                "is_visible": True,
            },
        ),
        (
            2,
            {
                "question": "Можно ли присутствовать на регистрации брака?",
                "answer": (
                    "Да, на торжественной регистрации брака могут присутствовать все желающие гости."
                ),
                "is_visible": True,
            },
        ),
        (
            3,
            {
                "question": "Планируется ли второй день?",
                "answer": (
                    'Да, второй день планируется на территории парк-отеля "Жемчужина": '
                    "мангальная зона и дом для отдыха."
                ),
                "is_visible": True,
            },
        ),
        (
            4,
            {
                "question": 'Как найти парк-отель "Жемчужина"?',
                "answer": (
                    "Адрес: г. Владимир, Южное шоссе, 23\n"
                    "Карта: https://yandex.ru/maps/-/CTRArMpi\n"
                    "Сайт: https://www.perlotel.ru/"
                ),
                "is_visible": True,
            },
        ),
        (
            5,
            {
                "question": "Можно ли предложить музыку для банкета?",
                "answer": (
                    "Да, музыкальные пожелания можно оставить в специальной форме на этом сайте."
                ),
                "is_visible": True,
            },
        ),
        (
            6,
            {
                "question": "Будет ли организован трансфер до места проведения?",
                "answer": "Информация о трансфере будет опубликована дополнительно.",
                "is_visible": True,
            },
        ),
        (
            7,
            {
                "question": "Будет ли мероприятие проходить на открытом воздухе?",
                "answer": (
                    'Основная часть банкета пройдет в ресторане "Гурман" при парк-отеле. '
                    "Дополнительную информацию по формату площадки сообщим ближе к дате мероприятия."
                ),
                "is_visible": True,
            },
        ),
    ]
    for order, defaults in faq_defaults:
        upsert_by_order(WeddingFAQ, page, order, defaults)
    WeddingFAQ.objects.filter(page=page, order__gt=7).update(is_visible=False)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("songs", "0003_sitevisit_importantannouncement"),
    ]

    operations = [
        migrations.RunPython(refine_wedding_copy, noop_reverse),
    ]
