from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Student, Teacher, Admin, Principal

@receiver(post_save, sender=Student)
def generate_student_number(sender, instance, created, **kwargs):
    if created and not instance.student_number:
        instance.student_number = f"STD{instance.id:03d}"
        instance.save(update_fields=['student_number'])

    if instance.user and not instance.user.school_id:
        instance.user.school_id = instance.student_number
        instance.user.save(update_fields=['school_id'])


@receiver(post_save, sender=Teacher)
def generate_employee_number_teacher(sender, instance, created, **kwargs):
    if created and not instance.employee_number:
        instance.employee_number = f"TCH{instance.id:03d}"
        instance.save(update_fields=['employee_number'])

    if instance.user and not instance.user.school_id:
        instance.user.school_id = instance.employee_number
        instance.user.save(update_fields=['school_id'])


@receiver(post_save, sender=Admin)
def generate_employee_number_admin(sender, instance, created, **kwargs):
    if created and not instance.employee_number:
        instance.employee_number = f"ADM{instance.id:03d}"
        instance.save(update_fields=['employee_number'])

    if instance.user and not instance.user.school_id:
        instance.user.school_id = instance.employee_number
        instance.user.save(update_fields=['school_id'])


@receiver(post_save, sender=Principal)
def generate_employee_number_principal(sender, instance, created, **kwargs):
    if created and not instance.employee_number:
        instance.employee_number = f"PRN{instance.id:03d}"
        instance.save(update_fields=['employee_number'])

    if instance.user and not instance.user.school_id:
        instance.user.school_id = instance.employee_number
        instance.user.save(update_fields=['school_id'])