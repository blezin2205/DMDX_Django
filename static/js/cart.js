var updateBtns = document.getElementsByClassName('update-cart')
var deleteBtns = document.getElementsByClassName('delete-supp-button')
var battonTest = document.getElementById('battonTest')


for(var a = 0; a < deleteBtns.length; a++) {
    deleteBtns[a].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action
        deleteSupply(productId, action)

    })
}

battonTest.addEventListener('click', function () {
    console.log("Click Hello")
})


for(var i = 0; i < updateBtns.length; i++) {
    updateBtns[i].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action
        console.log('id:', productId, 'action:', action)

        console.log('USER:', user)
        if (user === 'AnonymousUser') {
            console.log('Not logged in')
        } else {
            updateUserOrder(productId, action)
        }
    })
}


function deleteSupply(productId, action) {

    var url = 'delete_supply/'

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


function updateUserOrder(productId, action) {

    var url = 'update_item/'

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