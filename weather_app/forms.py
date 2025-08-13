from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import User


class CustomUserCreationForm(UserCreationForm):
    """Form đăng ký tài khoản tùy chỉnh"""
    
    email = forms.EmailField(
        required=True,
        help_text='Vui lòng nhập email hợp lệ.',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=False,
        help_text='Tên của bạn.',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=False,
        help_text='Họ của bạn.',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        help_text='Số điện thoại (không bắt buộc).',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tùy chỉnh help text và labels
        self.fields['username'].help_text = 'Bắt buộc. 150 ký tự trở xuống. Chỉ chứa chữ cái, số và @/./+/-/_'
        self.fields['password1'].help_text = 'Mật khẩu phải có ít nhất 8 ký tự và không được quá phổ biến.'
        self.fields['password2'].help_text = 'Nhập lại mật khẩu để xác nhận.'
        
        # Thêm CSS classes cho tất cả fields
        for field in self.fields.values():
            if hasattr(field.widget, 'attrs'):
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        """Kiểm tra email không được trùng lặp"""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email này đã được sử dụng.')
        return email
    
    def clean_phone_number(self):
        """Kiểm tra định dạng số điện thoại"""
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Loại bỏ khoảng trắng và ký tự đặc biệt
            phone = ''.join(filter(str.isdigit, phone))
            if len(phone) < 10:
                raise forms.ValidationError('Số điện thoại phải có ít nhất 10 chữ số.')
        return phone 





