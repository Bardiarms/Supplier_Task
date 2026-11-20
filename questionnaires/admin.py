from django.contrib import admin
from .models import Questionnaire, Question, Assignment


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1


@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):

    list_display = ("title", "created_by", "created_at")
    search_fields = ("title",)
    exclude = ("created_by",)

    inlines = [QuestionInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)
        

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "questionnaire",
        "product",
        "supplier_name",
        "assigned_by",
        "created_at"
    )

    list_filter = ("product__supplier",)

    exclude = ("assigned_by",)

    @admin.display(description="Supplier")
    def supplier_name(self, obj):
        return obj.product.supplier.name

    def save_model(self, request, obj, form, change):
        if not change:
            obj.assigned_by = request.user

        super().save_model(request, obj, form, change)