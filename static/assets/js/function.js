console.log("working fine");

const monthNames = ["Jan", "Feb", "Mar", "April", "May", "June",
    "July", "Aug", "Sept", "Oct", "Nov", "Dec"
];

$("#commentForm").submit(function (e) {
    e.preventDefault();

    let dt = new Date();
    let time = dt.getDay() + " " + monthNames[dt.getUTCMonth()] + ", " + dt.getFullYear()

    $.ajax({
        data: $(this).serialize(),

        method: $(this).attr("method"),

        url: $(this).attr("action"),

        dataType: "json",

        success: function (res) {
            console.log("Comment Saved to DB...");

            if (res.bool == true) {
                $("#review-res").html("Review added successfully.")
                $(".hide-comment-form").hide()
                $(".add-review").hide()

                let _html = '<div class="single-comment justify-content-between d-flex mb-30">'
                _html += '<div class="user justify-content-between d-flex">'
                _html += '<div class="thumb text-center">'
                _html += '<img src="https://thumbs.dreamstime.com/b/default-avatar-profile-vector-user-profile-default-avatar-profile-vector-user-profile-profile-179376714.jpg" alt="" />'
                _html += '<a href="#" class="font-heading text-brand">' + res.context.user + '</a>'
                _html += '</div>'

                _html += '<div class="desc">'
                _html += '<div class="d-flex justify-content-between mb-10">'
                _html += '<div class="d-flex align-items-center">'
                _html += '<span class="font-xs text-muted">' + time + ' </span>'
                _html += '</div>'

                for (var i = 1; i <= res.context.rating; i++) {
                    _html += '<i class="fas fa-star text-warning"></i>';
                }


                _html += '</div>'
                _html += '<p class="mb-10">' + res.context.review + '</p>'

                _html += '</div>'
                _html += '</div>'
                _html += ' </div>'

                $(".comment-list").prepend(_html)
            }


        }
    })
})



$(document).ready(function () {
    $(".filter-checkbox, #price-filter-btn").on("click", function () {
        console.log("A checkbox have been clicked");

        let filter_object = {}

        let min_price = $("#max_price").attr("min")
        let max_price = $("#max_price").val()

        filter_object.min_price = min_price;
        filter_object.max_price = max_price;

        $(".filter-checkbox").each(function () {
            let filter_value = $(this).val()
            let filter_key = $(this).data("filter") // vendor, category

            // console.log("Filter value is:", filter_value);
            // console.log("Filter key is:", filter_key);

            filter_object[filter_key] = Array.from(document.querySelectorAll('input[data-filter=' + filter_key + ']:checked')).map(function (element) {
                return element.value
            })
        })
        console.log("Filter Object is: ", filter_object);
        $.ajax({
            url: '/filter-products',
            data: filter_object,
            dataType: 'json',
            beforeSend: function () {
                console.log("Trying to filter product...");
            },
            success: function (response) {
                console.log(response.length);
                console.log("Data filtred successfully...");
                $(".totall-product").hide()
                $("#filtered-product").html(response.data)
            }
        })
    })

    $("#max_price").on("blur", function () {
        let min_price = $(this).attr("min")
        let max_price = $(this).attr("max")
        let current_price = $(this).val()

        // console.log("Current Price is:", current_price);
        // console.log("Max Price is:", max_price);
        // console.log("Min Price is:", min_price);

        if (current_price < parseInt(min_price) || current_price > parseInt(max_price)) {
            // console.log("Price Error Occured");

            min_price = Math.round(min_price * 100) / 100
            max_price = Math.round(max_price * 100) / 100


            // console.log("Max Price is:", min_Price);
            // console.log("Min Price is:", max_Price);

            alert("Price must between $" + min_price + ' and $' + max_price)
            $(this).val(min_price)
            $('#range').val(min_price)

            $(this).focus()

            return false

        }

    })

    // Add to cart functionality with event delegation
    $(document).on("click", ".add-to-cart-btn", function () {

        let this_val = $(this)
        let index = this_val.attr("data-index")

        // Check if we're on product detail page or product list page
        let quantity;
        if ($("#product-quantity").length) {
            // Product detail page - use the main quantity input
            quantity = $("#product-quantity").val()
        } else {
            // Product list page - use the hidden quantity input
            quantity = $(".product-quantity-" + index).val()
        }

        let product_title = $(".product-title-" + index).val()
        let product_id = $(".product-id-" + index).val()

        // Handle price - get from hidden input or current price display
        let product_price;
        if ($(".product-price-" + index).length) {
            product_price = $(".product-price-" + index).val()
        } else {
            // Fallback to getting price from display element
            product_price = $("#current-product-price").text()
        }

        let product_pid = $(".product-pid-" + index).val()
        let product_image = $(".product-image-" + index).val()

        // Debug: Kiểm tra dữ liệu
        console.log("Data being sent:", {
            id: product_id,
            title: product_title,
            price: product_price,
            pid: product_pid,
            image: product_image,
            qty: quantity
        });

        $.ajax({
            url: '/add-to-cart/',
            type: 'GET',
            data: {
                'id': product_id,
                'pid': product_pid,
                'image': product_image,
                'qty': quantity,
                'title': product_title,
                'price': product_price,
            },
            dataType: 'json',
            beforeSend: function () {
                console.log("Sending AJAX request...");
                this_val.html("Adding...");
            },
            success: function (response) {
                console.log("Success response:", response);
                this_val.html("✓ Added");
                if (response.totalcartitems) {
                    $(".cart-items-count").text(response.totalcartitems);
                }

                setTimeout(function () {
                    this_val.html('<i class="fi-rs-shopping-cart mr-5"></i>Add to cart');
                }, 2000);
            },
            error: function (xhr, status, error) {
                console.error("AJAX Error Details:");
                console.error("Status:", status);
                console.error("Error:", error);
                console.error("Response Text:", xhr.responseText);
                console.error("Status Code:", xhr.status);

                this_val.html("Error");
                setTimeout(function () {
                    this_val.html('<i class="fi-rs-shopping-cart mr-5"></i>Add to cart');
                }, 2000);
            }
        });
    })


    $(document).on("click", ".delete-product", function () {

        let product_id = $(this).attr("data-product")
        let this_val = $(this)

        console.log("PRoduct ID:", product_id);

        $.ajax({
            url: "/delete-from-cart",
            data: {
                "id": product_id
            },
            dataType: "json",
            beforeSend: function () {
                this_val.hide()
            },
            success: function (response) {
                this_val.show()
                $(".cart-items-count").text(response.totalcartitems)
                $("#cart-list").html(response.data)
            }
        })

    })

    // Handle quantity changes instantly
    $(document).on('input', '.qty-val', function () {
        let quantity = $(this).val();
        let product_id = $(this).data("product-id");
        let product_price = $(this).data("price");

        // Update row subtotal
        let subtotal = quantity * product_price;
        $(this).closest("tr").find(".product-subtotal").text("$" + subtotal.toFixed(2));

        // Update main cart totals
        let cart_total = 0;
        $(".product-subtotal").each(function () {
            cart_total += parseFloat($(this).text().replace("$", ""));
        });
        $("#cart-subtotal").text("$" + cart_total.toFixed(2));
        $("#cart-total").text("$" + cart_total.toFixed(2));

        // Update backend session
        $.ajax({
            url: "/update-cart",
            data: {
                "id": product_id,
                "qty": quantity,
            },
            dataType: "json",
            success: function (response) {
                $(".cart-items-count").text(response.totalcartitems);
                console.log("Cart updated on server");
            },
            error: function (xhr, status, error) {
                console.error("Failed to update cart on server:", error);
            }
        });
    });

    // Trigger input event on button click for compatibility
    $(document).on('click', '.qty-up, .qty-down', function (e) {
        e.preventDefault();
        const $qty = $(this).siblings('.qty-val');
        let val = parseInt($qty.val(), 10);
        if (isNaN(val) || val < 1) val = 1;

        if ($(this).hasClass('qty-up')) {
            val += 1;
        } else {
            val = Math.max(1, val - 1);
        }

        $qty.val(val).trigger('input'); // cập nhật UI + bắn AJAX /update-cart
    });
});





// Making Default Address
$(document).on("click", ".make-default-address", function () {
    let id = $(this).attr("data-address-id")
    let this_val = $(this)

    console.log("ID is:", id);
    console.log("Element is:", this_val);

    $.ajax({
        url: "/make-default-address",
        data: {
            "id": id
        },
        dataType: "json",
        success: function (response) {
            console.log("Address Made Default....");
            if (response.boolean == true) {

                $(".check").hide()
                $(".action_btn").show()

                $(".check" + id).show()
                $(".button" + id).hide()

            }
        }
    })
})


// Clear Cart
$(document).on("click", "#clear-cart-btn", function (e) {
    e.preventDefault();
    $.ajax({
        url: "/clear-cart/",
        dataType: "json",
        beforeSend: function () {
            console.log("Clearing cart...");
        },
        success: function (response) {
            $(".cart-items-count").text(response.totalcartitems);
            $("#cart-list").html(response.data);
        },
        error: function (xhr, status, error) {
            console.error("AJAX Error:", status, error);
        }
    });
});


// Adding to wishlist
$(document).on("click", ".add-to-wishlist", function () {
    let product_id = $(this).attr("data-product-item")
    let this_val = $(this)

    console.log("PRoduct ID IS", product_id);

    $.ajax({
        url: "/add-to-wishlist",
        data: {
            "id": product_id
        },
        dataType: "json",
        beforeSend: function () {
            console.log("Adding to wishlist...")
        },
        success: function (response) {
            this_val.html("<i class='fas fa-heart text-danger'></i>")
            if (response.bool === true) {
                console.log("Added to wishlist...");
                // Update wishlist counter
                if (response.wishlist_count) {
                    $(".wishlist-items-count").text(response.wishlist_count);
                }
            }
        }
    })
})

// Remove from wishlist
$(document).on("click", ".delete-wishlist-product", function () {
    let wishlist_id = $(this).attr("data-wishlist-product")
    let this_val = $(this)

    console.log("wishlist id is:", wishlist_id);

    $.ajax({
        url: "/remove-from-wishlist",
        data: {
            "id": wishlist_id
        },
        dataType: "json",
        beforeSend: function () {
            console.log("Deleting product from wishlist...");
        },
        success: function (response) {
            $("#wishlist-list").html(response.data)
            // Update wishlist counter
            if (response.wishlist_count !== undefined) {
                $(".wishlist-items-count").text(response.wishlist_count);
            }
        }
    })
})


$(document).on("submit", "#contact-form-ajax", function (e) {
    e.preventDefault()
    console.log("Submited...");

    let full_name = $("#full_name").val()
    let email = $("#email").val()
    let phone = $("#phone").val()
    let subject = $("#subject").val()
    let message = $("#message").val()

    console.log("Name:", full_name);
    console.log("Email:", email);
    console.log("Phone:", phone);
    console.log("Subject:", subject);
    console.log("MEssage:", message);

    $.ajax({
        url: "/ajax-contact-form",
        data: {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "subject": subject,
            "message": message,
        },
        dataType: "json",
        beforeSend: function () {
            console.log("Sending Data to Server...");
        },
        success: function (res) {
            console.log("Sent Data to server!");
            $(".contact_us_p").hide()
            $("#contact-form-ajax").hide()
            $("#message-response").html("Message sent successfully.")
        }
    })
})