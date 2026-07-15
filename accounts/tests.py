from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.serializers import RegistrationSerializer


class UserModelTests(APITestCase):
    def test_user_creation_hashes_password(self):
        user = User.objects.create_user(
            username='alice',
            email='Alice@Example.COM',
            password='StrongPass123!',
        )

        self.assertNotEqual(user.password, 'StrongPass123!')
        self.assertTrue(user.check_password('StrongPass123!'))
        self.assertEqual(user.email, 'alice@example.com')


class RegistrationValidationTests(APITestCase):
    password = 'StrongPass123!'

    def setUp(self):
        self.existing_user = User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password=self.password,
        )

    def registration_data(self, **overrides):
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': self.password,
            'password_confirm': self.password,
        }
        data.update(overrides)
        return data

    def test_duplicate_username_is_rejected(self):
        serializer = RegistrationSerializer(
            data=self.registration_data(username='existing')
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        serializer = RegistrationSerializer(
            data=self.registration_data(email='EXISTING@EXAMPLE.COM')
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_password_confirmation_mismatch_is_rejected(self):
        serializer = RegistrationSerializer(
            data=self.registration_data(password_confirm='DifferentPass123!')
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('password_confirm', serializer.errors)


class AuthenticationAPITests(APITestCase):
    password = 'StrongPass123!'

    def user_data(self, **overrides):
        data = {
            'username': 'sami',
            'email': 'sami@example.com',
            'first_name': 'Sami',
            'last_name': 'Ullah',
            'password': self.password,
            'password_confirm': self.password,
        }
        data.update(overrides)
        return data

    def create_user(self):
        return User.objects.create_user(
            username='sami',
            email='sami@example.com',
            first_name='Sami',
            last_name='Ullah',
            password=self.password,
        )

    def authenticate(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_registration_returns_201(self):
        response = self.client.post(
            reverse('auth-register'),
            self.user_data(),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)

    def test_registration_response_does_not_expose_passwords(self):
        response = self.client.post(
            reverse('auth-register'),
            self.user_data(),
            format='json',
        )

        self.assertNotIn('password', response.data)
        self.assertNotIn('password_confirm', response.data)
        self.assertNotIn('password', response.data['user'])
        self.assertNotIn('password_confirm', response.data['user'])

    def test_valid_login_returns_jwt_tokens_and_safe_user(self):
        self.create_user()

        response = self.client.post(
            reverse('auth-login'),
            {'username': 'sami', 'password': self.password},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['username'], 'sami')
        self.assertNotIn('password', response.data['user'])

    def test_invalid_login_is_rejected(self):
        self.create_user()

        response = self.client.post(
            reverse('auth-login'),
            {'username': 'sami', 'password': 'IncorrectPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_returns_new_access_token(self):
        user = self.create_user()
        refresh = RefreshToken.for_user(user)

        response = self.client.post(
            reverse('auth-token-refresh'),
            {'refresh': str(refresh)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_unauthenticated_current_user_is_rejected(self):
        response = self.client.get(reverse('auth-me'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_retrieve_profile(self):
        user = self.create_user()
        self.authenticate(user)

        response = self.client.get(reverse('auth-me'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], user.email)
        self.assertEqual(response.data['full_name'], 'Sami Ullah')

    def test_authenticated_user_can_update_allowed_profile_fields(self):
        user = self.create_user()
        self.authenticate(user)

        response = self.client.patch(
            reverse('auth-me'),
            {'first_name': 'Updated', 'last_name': 'Name', 'bio': 'Project manager'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(user.last_name, 'Name')
        self.assertEqual(user.bio, 'Project manager')

    def test_authenticated_user_cannot_update_protected_fields(self):
        user = self.create_user()
        self.authenticate(user)

        response = self.client.patch(
            reverse('auth-me'),
            {
                'username': 'changed',
                'email': 'changed@example.com',
                'password': 'PlainTextPass123!',
                'is_staff': True,
                'is_superuser': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.username, 'sami')
        self.assertEqual(user.email, 'sami@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password(self.password))
