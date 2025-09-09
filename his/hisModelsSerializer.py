
from rest_framework import serializers

from his.models import *


class UserLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLog
        fields = '__all__' # 指明所有模型类字段


class BladeRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BladeRecord
        fields = '__all__'  # 默认序列化所有字段

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # 获取视图传递的字段列表（如果有）
        requested_fields = self.context.get('fields', [])

        # 如果指定了字段列表，只返回这些字段
        if requested_fields:
            representation = {key: value for key, value in representation.items() if key in requested_fields}

        return representation


class BladeHoleParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = BladeHoleParameter
        fields = '__all__' # 指明所有模型类字段


class BladeSignImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BladeSignImage
        fields = '__all__' # 指明所有模型类字段


class ErrMsgSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrMsg
        fields = '__all__'


class DMMSnapSerializer(serializers.ModelSerializer):
    class Meta:
        model = DMMSnap
        fields = '__all__'


class BladePhaseLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BladePhaseLog
        fields = '__all__'


class AllBladePhaseStatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = AllBladePhaseStatistic
        fields = '__all__'


class BladeTypeCheckRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BladeTypeCheckRule
        fields = '__all__'


class BladeCheckVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BladeCheckVersion
        fields = '__all__'


class FlatnessReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlatnessReport
        fields = ['holeAngle', 'flatness']