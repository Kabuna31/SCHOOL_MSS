from django.test import TestCase
from django.core import mail
from django.utils import timezone
from accountsApp.models import User, Notice
from accountsApp.forms import AdminRegistrationForm, TeacherRegistrationForm

class NoticeEmailSignalTests(TestCase):
    def setUp(self):
        # Create users of each role with emails
        self.admin = User.objects.create_user(username='admin', password='pass', role='admin', email='admin@example.com')
        self.teacher = User.objects.create_user(username='teacher', password='pass', role='teacher', email='teacher@example.com')
        self.parent = User.objects.create_user(username='parent', password='pass', role='parent', email='parent@example.com')
        self.student = User.objects.create_user(username='student', password='pass', role='student', email='student@example.com')

    def test_notice_creation_sends_emails(self):
        Notice.objects.create(title='Holiday', message='School will remain closed tomorrow', created_by=self.admin)
        self.assertEqual(len(mail.outbox), 4)
        subjects = {m.subject for m in mail.outbox}
        self.assertIn('Notice: Holiday', subjects)

    def test_notice_update_does_not_resend(self):
        n = Notice.objects.create(title='Event', message='Annual day', created_by=self.admin)
        self.assertEqual(len(mail.outbox), 4)
        mail.outbox.clear()
        n.message = 'Annual day updated details'
        n.save()  # should not trigger new emails
        self.assertEqual(len(mail.outbox), 0)


class AdminTeacherEmailValidationTests(TestCase):
    def test_admin_email_requires_dot_admin(self):
        form = AdminRegistrationForm(data={
            'username': 'admin2',
            'email': 'abhi@gmail.com',  # missing .admin
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('.admin', form.errors['email'][0])

    def test_admin_email_accepts_dot_admin(self):
        form = AdminRegistrationForm(data={
            'username': 'admin3',
            'email': 'abhi.admin@gmail.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
        })
        self.assertTrue(form.is_valid(), msg=form.errors)
        user = form.save()
        self.assertEqual(user.role, 'admin')

    def test_teacher_email_requires_dot_teacher(self):
        form = TeacherRegistrationForm(data={
            'username': 'teacher2',
            'email': 'abhi@gmail.com',  # missing .teacher
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('.teacher', form.errors['email'][0])

    def test_teacher_email_accepts_dot_teacher(self):
        form = TeacherRegistrationForm(data={
            'username': 'teacher3',
            'email': 'abhi.teacher@gmail.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
        })
        self.assertTrue(form.is_valid(), msg=form.errors)
        user = form.save()
        self.assertEqual(user.role, 'teacher')
