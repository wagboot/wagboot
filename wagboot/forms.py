# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import forms
from django.contrib.auth import forms as auth_forms


class PasswordResetForm(auth_forms.PasswordResetForm):
    def get_user(self):
        return next(self.get_users(self.cleaned_data['email']), None)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            user = self.get_user()
            if not user:
                raise forms.ValidationError("No user with such email found.")
        return email

    def save(self, *args, **kwargs):
        raise ValueError("save is not used in this form")


class SetPasswordForm(auth_forms.SetPasswordForm):
    reset_token = forms.CharField(max_length=200, widget=forms.HiddenInput, required=False)
    reset_uid = forms.CharField(max_length=200, widget=forms.HiddenInput, required=False)


