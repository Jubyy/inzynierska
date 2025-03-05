from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ShoppingListItem
from .forms import ShoppingListItemForm
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

@login_required
def shopping_list(request):
    items = ShoppingListItem.objects.filter(user=request.user)
    return render(request, 'shopping/shopping_list.html', {'items': items})

@login_required
def add_to_shopping_list(request):
    if request.method == 'POST':
        form = ShoppingListItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            messages.success(request, 'Dodano produkt do listy zakupów.')
            if 'print_now' in request.POST:
                return redirect('print_shopping_list')
            return redirect('shopping_list')
    else:
        form = ShoppingListItemForm(initial={
            'name': request.GET.get('name', ''),
            'quantity': request.GET.get('quantity', ''),
            'unit': request.GET.get('unit', ''),
            'recipe_name': request.GET.get('recipe_name', '')
        })

    return render(request, 'shopping/add_to_list.html', {'form': form})

@login_required
def print_shopping_list(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="lista_zakupow.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    y = 750

    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, y, "Lista zakupów:")
    y -= 20

    items = ShoppingListItem.objects.filter(user=request.user)

    for item in items:
        p.setFont("Helvetica", 12)
        text = f"{item.name} - {item.quantity} {item.unit} (do: {item.recipe_name})"
        p.drawString(100, y, text)
        y -= 15

    p.save()
    return response