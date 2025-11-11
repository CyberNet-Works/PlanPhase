# Based on this task/bug tracker implementation, here are some potential additions to consider:

# 1. Priority Fields:
# - Add severity/impact level (critical, high, medium, low)

# 2. Tracking Fields:
# - Add resolution_notes field for closure documentation
# - Add closing_notes field for final documentation/lessons learned

# 3. Custom States:
# - Add "in_review" status for QA/verification
# - Add "reopened" status for recurring issues
# - Add "on_hold" status distinct from blocked

# 4. Metrics:
# - Add SLA tracking fields
# - Add first_response_time field
# - Add resolution_time metrics

# 5. Categories:
# - Add problem_type (bug, feature, improvement)
# - Add component/module field
# - Add environment field (dev, staging, prod)

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.db.models import F, ExpressionWrapper, DateTimeField

User = get_user_model()


# --------------------------------
# Custom QuerySet with Filters
# --------------------------------
class ProblemQuerySet(models.QuerySet):

    def new(self):
        return self.filter(status="new")

    def active(self):
        return self.filter(status__in=["engaged", "blocked"])

    def done(self):
        return self.filter(status="done")

    def cancelled(self):
        return self.filter(status="cancelled")

    def overdue(self):

        return (
            self.filter(
                etd__isnull=False,
                started_at__isnull=False,
                status__in=["new", "engaged", "blocked"],
            )
            .annotate(
                deadline=ExpressionWrapper(
                    F("started_at") + F("etd"), output_field=DateTimeField()
                )
            )
            .filter(deadline__lt=now())
        )

    def tasks(self):
        return self.filter(scale="task")

    def missions(self):
        return self.filter(scale="mission")

    def by_chief(self, user):
        return self.filter(chief=user)

    def by_executive(self, user):
        return self.filter(executive=user)


class ProblemManager(models.Manager):
    def get_queryset(self):
        return ProblemQuerySet(self.model, using=self._db)

    # Expose custom QuerySet methods directly on Manager
    def new(self):
        return self.get_queryset().new()

    def active(self):
        return self.get_queryset().active()

    def done(self):
        return self.get_queryset().done()

    def cancelled(self):
        return self.get_queryset().cancelled()

    def overdue(self):
        return self.get_queryset().overdue()

    def tasks(self):
        return self.get_queryset().tasks()

    def missions(self):
        return self.get_queryset().missions()

    def by_chief(self, user):
        return self.get_queryset().by_chief(user)

    def by_executive(self, user):
        return self.get_queryset().by_executive(user)


# --------------------------------
# Tag
# --------------------------------
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# --------------------------------
# Problem (Core Model)
# --------------------------------
class Problem(models.Model):
    SCALE_CHOICES = [
        ("task", "Task"),  # small unit of work
        ("mission", "Mission"),  # multiple tasks grouped
    ]

    STATUS_CHOICES = [
        ("new", "New"),
        ("engaged", "Engaged"),
        ("blocked", "Blocked"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    scale = models.CharField(
        max_length=20,
        choices=SCALE_CHOICES,
        help_text="Task = small. Mission = larger grouped effort.",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="problems_parent",
        help_text="Optional parent if this belongs under a mission/problem.",
    )

    chief = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problems_chief",
        help_text="Accountable person (decision + ownership).",
    )

    executive = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problems_executive",
        help_text="Actively engaged in performing the work.",
    )

    advisors = models.ManyToManyField(
        User,
        blank=True,
        related_name="problems_advisors",
        help_text="Advisors/support/sponsors, not executing directly.",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
        help_text="new / engaged / blocked / done / cancelled",
    )

    priority = models.FloatField(default=0)

    etd = models.DurationField(
        null=True, blank=True, help_text="Estimated Time of Duration (user-defined)."
    )

    created_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="problems_created_by",
        help_text="User who initially logged the problem.",
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="problems_updated_by",
        help_text="User who last updated this problem.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set automatically when status becomes 'engaged'.",
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set automatically when status becomes 'done' or 'cancelled'.",
    )

    tags = models.ManyToManyField(Tag, blank=True, related_name="problems_tags")

    objects = ProblemManager()

    class Meta:
        ordering = ["priority", "-created_at"]

    # --------------------------------
    # Auto Timestamp + Status Logic
    # --------------------------------
    def save(self, *args, user=None, **kwargs):
        """
        Custom save() method:
        - Tracks who updated the object (updated_by)
        - Automatically sets started_at and closed_at timestamps
        - Logs field changes into ProblemHistory with old/new values
        """

        # --- If this is an update (not a new object) ---
        if self.pk:
            old = Problem.objects.get(pk=self.pk)  # fetch current DB state

            # 1. Detect changes and log to ProblemHistory
            track_fields = [
                "title",
                "description",
                "status",
                "priority",
                "chief",
                "executive",
                "etd",
                "scale",
                "started_at",
                "closed_at",
            ]
            for field in track_fields:
                old_value = getattr(old, field)
                new_value = getattr(self, field)
                if old_value != new_value:
                    ProblemHistory.objects.create(
                        problem=self,
                        field=field,
                        old_value=old_value,
                        new_value=new_value,
                        changed_by=user,  # who made this change
                    )

            # 2. Set updated_by (last person who changed this)
            if user:
                self.updated_by = user

        else:
            # --- New object (first-time create) ---
            if user:
                self.created_by = user  # who created it
                self.updated_by = user  # also count as first update

        # --- Auto Timestamp Logic ---
        # Set started_at when status becomes 'engaged'
        if self.status == "engaged" and self.started_at is None:
            self.started_at = now()

        # Set closed_at when finished or cancelled
        if self.status in ["done", "cancelled"] and self.closed_at is None:
            self.closed_at = now()

        # Finally, save to DB
        super().save(*args, **kwargs)

    # def save(self, *args, **kwargs):
    #     # Set started_at when work begins
    #     if self.status == "engaged" and self.started_at is None:
    #         self.started_at = now()

    #     # Set closed_at when it's finished or cancelled
    #     if self.status in ["done", "cancelled"] and self.closed_at is None:
    #         self.closed_at = now()

    #     super().save(*args, **kwargs)

    # --------------------------------
    # Properties (Real-Time)
    # --------------------------------
    @property
    def expected_end(self):
        """Real-time: created_at + etd."""
        if self.created_at and self.etd:
            return self.created_at + self.etd
        return None

    @property
    def real_duration(self):
        """
        Real-time:
        - If started_at missing → None
        - If closed_at exists → closed_at - started_at
        - Else → now - started_at
        """
        if not self.started_at:
            return None
        if self.closed_at:
            return self.closed_at - self.started_at
        return now() - self.started_at

    @property
    def active_state(self):
        """new / active / inactive (for filters/grouping UI)"""
        if self.status == "new":
            return "new"
        if self.status in ["engaged", "blocked"]:
            return "active"
        return "inactive"

    def __str__(self):
        return self.title


# --------------------------------
# Comments
# --------------------------------
class ProblemComment(models.Model):
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="problem_comments"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="problems_comment_authors",
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="problem_comment_replies",
    )

    def __str__(self):
        return f"{self.author} → {self.problem}"


# --------------------------------
# Attachments
# --------------------------------
class ProblemAttachment(models.Model):
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="problem_attachments"
    )
    file = models.FileField(upload_to="problem_attachments/")
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="problems_attachment_uploaders",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name


# --------------------------------
# History (Audit Trail)
# --------------------------------
class ProblemHistory(models.Model):
    FIELD_CHOICES = [
        ("title", "Title"),
        ("description", "Description"),
        ("status", "Status"),
        ("priority", "Priority"),
        ("chief", "Chief"),
        ("executive", "Executive"),
        ("etd", "Estimated Duration"),
        ("scale", "Scale"),
        ("started_at", "Started At"),
        ("closed_at", "Closed At"),
    ]

    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="problem_history"
    )
    field = models.CharField(max_length=50, choices=FIELD_CHOICES)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="problems_history_changed_by",
    )
    changed_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.problem} – {self.field}"
