from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.db.utils import ProgrammingError, OperationalError
from .models import UserProfile

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password'
    }))

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    phone = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Enter your phone number'
    }))
    address = forms.CharField(required=True, widget=forms.Textarea(attrs={
        'class': 'form-control', 
        'placeholder': 'Enter your address', 
        'rows': 3
    }))

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'phone', 'address')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Try to create or update profile if the table exists
            try:
                # Get or create profile instead of always creating
                phone = self.cleaned_data.get('phone') or ''  # Default to empty string, not None
                address = self.cleaned_data.get('address') or ''  # Default to empty string, not None
                
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'phone': phone,
                        'address': address
                    }
                )
                
                # Update profile if it already existed
                if not created:
                    profile.phone = phone
                    profile.address = address
                    profile.save()
            except (ProgrammingError, OperationalError):
                # If the table doesn't exist, just continue without creating profile
                pass
        
        return user
