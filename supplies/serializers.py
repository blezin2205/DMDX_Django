from django.conf import settings
from django.utils import timezone

from .models import *
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class GeneralSupplySerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneralSupply
        fields = '__all__'

    def to_representation(self, instance):
        self.fields['general'] = SupplySerializer(read_only=True, many=True)
        self.fields['category'] = CategorySerializer(read_only=True)
        return super(GeneralSupplySerializer, self).to_representation(instance)


class SupplySaveFromScanSerializer(serializers.ModelSerializer):
    expiredDate = serializers.DateField(format="%d-%m-%Y", input_formats=['%d-%m-%Y', 'iso-8601', '%y%m%d'], allow_null=True)

    class Meta:
        model = SupplySaveFromScanApiModel
        fields = '__all__'

class SupplySerializer(serializers.ModelSerializer):
    dateCreated = serializers.DateField(format="%d-%m-%Y", input_formats=['%d-%m-%Y', 'iso-8601'], default=timezone.now().date())
    expiredDate = serializers.DateField(format="%d-%m-%Y", input_formats=['%d-%m-%Y', 'iso-8601', '%y%m%d'], allow_null=True)
    name = serializers.CharField(source='general_supply', allow_null=True)
    ref = serializers.CharField(source='general_supply.ref', allow_null=True)
    smn_code = serializers.CharField(source='general_supply.SMN_code', allow_null=True)
    category = serializers.CharField(source='category.name', allow_null=True)
    package_and_tests = serializers.CharField(source='general_supply.package_and_tests', allow_null=True)

    class Meta:
        model = Supply
        fields = ['id', 'supplyLot', 'dateCreated', 'expiredDate', 'name', 'ref', 'category', 'count', 'countOnHold', 'smn_code', 'package_and_tests']

    # def to_representation(self, instance):
    #     self.fields['category'] = CategorySerializer(read_only=True)
    #     return super(SupplySerializer, self).to_representation(instance)


class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = '__all__'

class SupplyInOrderSerializer(serializers.ModelSerializer):
    name = serializers.SlugRelatedField(
        read_only=True,
        slug_field='name',
        source='supply_in_storage'
    )
    ref = serializers.SlugRelatedField(

        read_only=True,
        slug_field='ref',
        source='supply_in_storage'
    )
    lot = serializers.CharField(max_length=20, allow_null=True)
    dateCreated = serializers.DateField(source='date_created', input_formats='%d-%m-%Y')
    expiredDate = serializers.DateField(source='date_expired', input_formats='%d-%m-%Y')
    countInOrder = serializers.IntegerField(source='count_in_order')

    class Meta:
        model = SupplyInOrder
        fields = ['name',
                  'ref',
                  'lot',
                  'dateCreated',
                  'expiredDate', 'countInOrder']




class OrderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dateCreated = serializers.DateField(input_formats='%d-%m-%Y')
    dateSent = serializers.DateField(input_formats='%d-%m-%Y', allow_null=True)
    isComplete = serializers.BooleanField()
    place = PlaceSerializer(read_only=True)
    # supplies = SupplyInOrderSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'dateCreated', 'dateSent', 'isComplete', 'place']





class RegistrationSerializer(serializers.ModelSerializer):
    """
    Creates a new user.
    Email, username, and password are required.
    Returns a JSON web token.
    """

    # The password must be validated and should not be read by the client
    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True,
    )

    # The client should not be able to send a token along with a registration
    # request. Making `token` read-only handles that for us.
    token = serializers.CharField(max_length=255, read_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'password', 'token',)

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'