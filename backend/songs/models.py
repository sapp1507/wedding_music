from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class WeddingPage(models.Model):
    groom_name = models.CharField("Имя жениха", max_length=80, default="Алексей")
    bride_name = models.CharField("Имя невесты", max_length=80, default="Мария")
    wedding_date = models.DateTimeField(
        "Дата и время свадьбы",
        default=timezone.now,
    )
    timezone_name = models.CharField(
        "Часовой пояс",
        max_length=64,
        default="Europe/Moscow",
    )
    hero_kicker = models.CharField(
        "Надпись над заголовком",
        max_length=160,
        default="Свадебное приглашение",
    )
    invitation_text = models.TextField(
        "Текст приглашения",
        default=(
            "В нашей жизни скоро состоится важное событие - наша свадьба! "
            "Мы приглашаем вас и будем рады провести этот особенный день "
            "в кругу самых близких людей!"
        ),
    )
    location_title = models.CharField(
        "Заголовок места",
        max_length=160,
        default="Место проведения",
    )
    location_name = models.CharField(
        "Название площадки",
        max_length=180,
        default="Мономах",
    )
    location_address = models.CharField(
        "Адрес",
        max_length=300,
        default="Мономах, Владимир, улица Гоголя, 20",
    )
    location_map_url = models.URLField(
        "Ссылка на карту",
        blank=True,
        default="https://yandex.ru/maps/-/CTUQy69U",
    )
    footer_title = models.CharField(
        "Финальный заголовок",
        max_length=180,
        default="Будем счастливы видеть вас!",
    )
    footer_text = models.TextField(
        "Финальный текст",
        blank=True,
        default="Спасибо, что разделите с нами этот день.",
    )
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "страница свадьбы"
        verbose_name_plural = "страница свадьбы"

    def __str__(self):
        return f"{self.groom_name} и {self.bride_name}"

    @classmethod
    def current(cls):
        page = cls.objects.order_by("id").first()
        if page:
            return page
        return cls.objects.create()


class WeddingEvent(models.Model):
    page = models.ForeignKey(
        WeddingPage,
        verbose_name="Страница",
        related_name="events",
        on_delete=models.CASCADE,
    )
    title = models.CharField("Название", max_length=180)
    description = models.CharField("Описание/адрес", max_length=300, blank=True)
    starts_at = models.DateTimeField("Время")
    order = models.PositiveIntegerField("Порядок", default=0)
    is_visible = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["order", "starts_at", "id"]
        verbose_name = "событие программы"
        verbose_name_plural = "программа свадьбы"

    def __str__(self):
        return self.title


class WeddingFAQ(models.Model):
    page = models.ForeignKey(
        WeddingPage,
        verbose_name="Страница",
        related_name="faqs",
        on_delete=models.CASCADE,
    )
    question = models.CharField("Вопрос", max_length=240)
    answer = models.TextField("Ответ")
    order = models.PositiveIntegerField("Порядок", default=0)
    is_visible = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "вопрос и ответ"
        verbose_name_plural = "вопросы и ответы"

    def __str__(self):
        return self.question


class WeddingInfoBlock(models.Model):
    page = models.ForeignKey(
        WeddingPage,
        verbose_name="Страница",
        related_name="info_blocks",
        on_delete=models.CASCADE,
    )
    title = models.CharField("Заголовок", max_length=180)
    body = models.TextField("Текст")
    link_label = models.CharField("Текст ссылки", max_length=120, blank=True)
    link_url = models.URLField("Ссылка", blank=True)
    order = models.PositiveIntegerField("Порядок", default=0)
    is_visible = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "информационный блок"
        verbose_name_plural = "информационные блоки"

    def __str__(self):
        return self.title


class GuestRSVP(models.Model):
    class Attendance(models.TextChoices):
        YES = "yes", "Приду"
        NO = "no", "Не смогу"
        MAYBE = "maybe", "Уточню позже"

    guest_name = models.CharField("Имя гостя", max_length=120)
    attendance = models.CharField(
        "Придет ли гость",
        max_length=12,
        choices=Attendance.choices,
    )
    guests_count = models.PositiveSmallIntegerField("Количество гостей", default=1)
    phone = models.CharField("Телефон", max_length=40, blank=True)
    comment = models.TextField("Комментарий", blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "ответ гостя"
        verbose_name_plural = "ответы гостей"

    def __str__(self):
        return f"{self.guest_name}: {self.get_attendance_display()}"


class ImportantAnnouncement(models.Model):
    title = models.CharField("Заголовок", max_length=180)
    body = models.TextField("Текст")
    is_active = models.BooleanField("Активна", default=False)
    show_to_guests = models.BooleanField("Показывать гостям", default=True)
    archived = models.BooleanField("В архиве", default=False)
    view_count = models.PositiveIntegerField("Просмотров", default=0)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ["-is_active", "-created_at"]
        verbose_name = "важная информация"
        verbose_name_plural = "важная информация"

    def clean(self):
        super().clean()
        if self.archived and self.is_active:
            raise ValidationError("Архивная модалка не может быть активной.")

    def save(self, *args, **kwargs):
        self.clean()
        if self.is_active and self.show_to_guests and not self.archived:
            ImportantAnnouncement.objects.exclude(pk=self.pk).filter(
                is_active=True,
                show_to_guests=True,
                archived=False,
            ).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @classmethod
    def active_for_guests(cls):
        return cls.objects.filter(
            is_active=True,
            show_to_guests=True,
            archived=False,
        ).order_by("-created_at").first()


class SiteVisit(models.Model):
    visitor_id = models.CharField("ID посетителя", max_length=64, unique=True)
    first_seen_at = models.DateTimeField("Первый визит", auto_now_add=True)
    last_seen_at = models.DateTimeField("Последний визит", auto_now=True)
    visit_count = models.PositiveIntegerField("Визитов", default=1)
    user_agent = models.TextField("User-Agent", blank=True)
    last_path = models.CharField("Последний путь", max_length=240, blank=True)

    class Meta:
        ordering = ["-last_seen_at"]
        verbose_name = "посетитель сайта"
        verbose_name_plural = "посетители сайта"

    def __str__(self):
        return self.visitor_id


class SongRequest(models.Model):
    class Moment(models.TextChoices):
        DINNER = "dinner", "Фон на банкете"
        DANCE = "dance", "Танцы"
        SLOW = "slow", "Медляк"
        WISHLIST = "wishlist", "Просто хочу услышать"

    guest_name = models.CharField("Имя гостя", max_length=100)
    song_title = models.CharField("Название трека", max_length=200, blank=True)
    artist = models.CharField("Исполнитель", max_length=200, blank=True)
    link = models.URLField("Ссылка", blank=True)
    moment = models.CharField(
        "Когда включить",
        max_length=20,
        choices=Moment.choices,
        blank=True,
    )
    comment = models.TextField("Комментарий", blank=True)
    approved = models.BooleanField("Одобрено", default=False)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "заявка на трек"
        verbose_name_plural = "заявки на треки"

    def clean(self):
        super().clean()
        if not self.song_title and not self.link:
            raise ValidationError("Укажите название трека или ссылку.")

    def __str__(self):
        title = self.song_title or self.link
        return f"{self.guest_name}: {title}"
