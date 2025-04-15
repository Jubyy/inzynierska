from .models import ExpiryNotification

def notifications_processor(request):
    """
    Dodaje liczbę nieprzeczytanych powiadomień do kontekstu wszystkich widoków.
    """
    if request.user.is_authenticated:
        unread_count = ExpiryNotification.objects.filter(
            user=request.user, is_read=False
        ).count()
        return {
            'unread_notifications_count': unread_count,
        }
    return {
        'unread_notifications_count': 0,
    } 