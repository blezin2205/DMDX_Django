var updateBtns = document.getElementsByClassName('update-cart')
var updateDetailBtns = document.getElementsByClassName('update-cart-detail')
var updateOrderStatusBtns = document.getElementsByClassName('update-order-status')
var deleteBtns = document.getElementsByClassName('delete-supp-button')
var battonTest = document.getElementById('battonTest')


for(var a = 0; a < deleteBtns.length; a++) {
    deleteBtns[a].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action

        var url = 'delete_supply/'
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