from rest_framework import serializers

from .models import GradeScale, GradeScaleRule, MarksSubmission


class GradeScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeScale
        fields = "__all__"


class GradeScaleRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeScaleRule
        fields = "__all__"


class MarksSubmissionSelectionSerializer(serializers.Serializer):
    exam_id = serializers.IntegerField(min_value=1)
    classroom_id = serializers.IntegerField(min_value=1)
    subject_id = serializers.IntegerField(min_value=1)


class MarksSubmissionListSerializer(serializers.Serializer):
    exam_id = serializers.IntegerField(min_value=1)
    classroom_id = serializers.IntegerField(min_value=1)


class MarksSubmissionActionSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class MarksSubmissionSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source="exam.name", read_only=True)
    classroom_name = serializers.StringRelatedField(source="classroom")
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = MarksSubmission
        fields = (
            "id",
            "exam",
            "exam_name",
            "classroom",
            "classroom_name",
            "subject",
            "subject_name",
            "status",
            "submitted_at",
            "approved_at",
            "released_at",
        )
