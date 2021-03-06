var updateBtns = document.getElementsByClassName('update-cart')
var updateDetailBtns = document.getElementsByClassName('update-cart-detail')
var updateOrderStatusBtns = document.getElementsByClassName('update-order-status')
var deleteBtns = document.getElementsByClassName('delete-supp-button')
var deleteSuppInOrderBtns = document.getElementsByClassName('delete-suppinorder-button')
var update_count_in_order = document.getElementsByClassName('update-order-count')

for(var a = 0; a < deleteBtns.length; a++) {
    deleteBtns[a].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action

        var url = 'delete_supply/'
        senadAction(productId, action, url)

    })
}

for(var a = 0; a < update_count_in_order.length; a++) {
    update_count_in_order[a].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action

        var url = '/update_order_count/'
        senadAction(productId, action, url)

    })
}

for(var a = 0; a < deleteSuppInOrderBtns.length; a++) {
    deleteSuppInOrderBtns[a].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action
        console.log('Prinet delete action')

        var url = '/delete_supply_in_order/'
        senadAction(productId, action, url)

    })
}

for(var a = 0; a < updateOrderStatusBtns.length; a++) {
    updateOrderStatusBtns[a].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action
        var url = '/orders_update_status/'
        senadAction(productId, action, url)
    })
}

for(var i = 0; i < updateBtns.length; i++) {
    updateBtns[i].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action
        console.log('id:', productId, 'action:', action)

        console.log('Print log')
         var url = '/update_item/'

        console.log('USER:', user)
        if (user === 'AnonymousUser') {
            console.log('Not logged in')
        } else {
            senadAction(productId, action, url)
        }
    })
}

for(var i = 0; i < updateDetailBtns.length; i++) {
    updateDetailBtns[i].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action
        console.log('id:', productId, 'action:', action)

        console.log('Print log')
         var url = 'update_item/'

        console.log('USER:', user)
        if (user === 'AnonymousUser') {
            console.log('Not logged in')
        } else {
            senadAction(productId, action, url)
        }
    })
}


function senadAction(productId, action, url) {
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({'productId': productId, 'action': action})
    })

     .then((response) =>{
            return response.json()
        })

    .then((data) => {
        console.log('data:', data)
        location.reload()
        })
}