from django.contrib import admin
from .models import Problem, Tag, ProblemComment, ProblemAttachment, ProblemHistory


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "status",
        "scale",
        "chief",
        "executive",
        "priority",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "scale", "priority", "chief", "executive", "tags")

    search_fields = (
        "title",
        "description",
        "chief__username",
        "executive__username",
    )

    autocomplete_fields = (
        "chief",
        "executive",
        "advisors",
        "created_by",
        "updated_by",
    )

    filter_horizontal = ("advisors", "tags")


admin.site.register(Tag)
admin.site.register(ProblemComment)
admin.site.register(ProblemAttachment)
admin.site.register(ProblemHistory)
