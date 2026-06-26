from django.core.exceptions import ValidationError
from django.db import models


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
