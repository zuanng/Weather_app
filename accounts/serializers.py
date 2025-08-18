from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
import re

User = get_user_model()

class CustomUserCreationSerializer(serializers.ModelSerializer):
    """Serializer đăng ký tài khoản tùy chỉnh"""
    
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text='Mật khẩu phải có ít nhất 8 ký tự và không được quá phổ biến.',
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        help_text='Nhập lại mật khẩu để xác nhận.',
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'password', 'password_confirm')
        extra_kwargs = {
            'email': {
                'required': True,
                'help_text': 'Vui lòng nhập email hợp lệ.'
            },
            'username': {
                'help_text': 'Bắt buộc. 150 ký tự trở xuống. Chỉ chứa chữ cái, số và @/./+/-/_'
            },
            'first_name': {
                'required': False,
                'help_text': 'Tên của bạn.'
            },
            'last_name': {
                'required': False,
                'help_text': 'Họ của bạn.'
            },
            'phone_number': {
                'required': False,
                'help_text': 'Số điện thoại (không bắt buộc).'
            }
        }
    
    def validate_email(self, value):
        """Kiểm tra email đã tồn tại chưa"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email này đã được sử dụng.')
        return value
    
    def validate_username(self, value):
        """Kiểm tra username đã tồn tại chưa"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Tên đăng nhập này đã được sử dụng.')
        return value
    
    def validate_phone_number(self, value):
        """Kiểm tra định dạng số điện thoại"""
        if value:
            # Loại bỏ khoảng trắng và ký tự đặc biệt
            phone = ''.join(filter(str.isdigit, value))
            if len(phone) < 10:
                raise serializers.ValidationError('Số điện thoại phải có ít nhất 10 chữ số.')
            return phone
        return value
    
    def validate_password(self, value):
        """Kiểm tra mật khẩu theo Django password validators"""
        validate_password(value)
        return value
    
    def validate(self, attrs):
        """Kiểm tra password và password_confirm khớp nhau"""
        password = attrs.get('password')
        password_confirm = attrs.pop('password_confirm', None)
        
        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': 'Mật khẩu xác nhận không khớp.'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Tạo user mới với email verification"""
        # Loại bỏ password_confirm vì đã validate
        validated_data.pop('password_confirm', None)
        
        # Tạo user với password đã hash
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            email_verified=False  # Mặc định chưa verify email
        )
        
        # Tự động tạo email verification token
        user.generate_email_verification_token()
        
        return user