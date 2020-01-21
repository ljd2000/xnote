if (window.xnote == undefined) {
    window.xnote = {};
}

window.xnote.showDialog = function(title, html) {
    if (isMobile()) {
        var area = ['100%', '100%'];
    } else {
        var area = ['600px', '80%'];
    }

    layer.open({
        type: 1,
        title: title,
        shadeClose: true,
        area: area,
        content: html,
        scrollbar: false
    });
}

// 询问函数，原生prompt的替代方案
xnote.prompt = function(title, defaultValue, callback) {
    if (layer && layer.prompt) {
        // 使用layer弹层
        layer.prompt({
            title: title,
            value: defaultValue,
            scrollbar: false,
            area: ['400px', '300px']
        },
        function(value, index, element) {
            callback(value);
            layer.close(index);
        })
    } else {
        var result = prompt(title, defaultValue);
        callback(result);
    }
};

// 确认函数
xnote.confirm = function(message, callback) {
    if (layer && layer.confirm) {
        layer.confirm(message,
        function(index) {
            callback(true);
            layer.close(index);
        })
    } else {
        var result = confirm(message);
        callback(result);
    }
};

// 警告函数
xnote.alert = function(message) {
    if (layer && layer.alert) {
        layer.alert(message);
    } else {
        alert(message);
    }
};

window.xnote.toast = function(message, time) {
    if (time == undefined) {
        time = 1000;
    }
    var maxWidth = $(document.body).width();
    var fontSize = 14;
    var toast = $("<div>").css({
        "margin": "0 auto",
        "position": "fixed",
        "left": 0,
        "top": "24px",
        "font-size": fontSize,
        "padding": "14px 18px",
        "border-radius": "4px",
        "background": "#000",
        "opacity": 0.7,
        "color": "#fff",
        "line-height": "22px",
        "z-index": 1000
    });
    toast.text(message);

    $(document.body).append(toast);
    var width = toast.outerWidth();
    var left = (maxWidth - width) / 2;
    if (left < 0) {
        left = 0;
    }
    toast.css("left", left);
    setTimeout(function() {
        toast.remove();
    },
    time);
}

// 兼容之前的方法
window.showToast = window.xnote.toast;
