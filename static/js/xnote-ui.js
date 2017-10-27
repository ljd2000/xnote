var XUI = function (window) {
  // 处理select标签选中情况
  function initSelect() {  
    $("select").each(function (index, ele) {
      var self = $(ele);
      var children = self.children();
      // 使用$.val() 会取到第一个select标签值
      var value = self.attr("value");
      for (var i = 0; i < children.length; i++) {
        var child = children[i];
        if (value == child.value) {
          child.selected = "selected";
        }
      }
    });
  }

  // 点击跳转链接的按钮
  $(".link-btn").click(function () {
      var link = $(this).attr("href");
      var confirmMessage = $(this).attr("confirm-message");
      if (confirmMessage) {
        var check = confirm(confirmMessage);
        if (check) {
          window.location.href = link;
        }
      } else {
        window.location.href = link;
      }
  })

  // 点击prompt按钮
  $(".prompt-btn").click(function () {
      var action = $(this).attr("action");
      var message = $(this).attr("message");
      var message = prompt(message);
      if (message != "" && message) {
          $.get(action + encodeURIComponent(message), function () {
              window.location.reload();
          })
      }
  })

  // 点击激活对话框的按钮
  $(".dialog-btn").click(function () {
    var dialogUrl = $(this).attr("dialog-url");
    var dialogId = $(this).attr("dialog-id");
    if (dialogUrl) {
      // 通过新的HTML页面获取dialog
      $.get(dialogUrl, function (respHtml) {
        $(document.body).append(respHtml);
        doModal(dialogId);
        initElementProcessors();
        // 重新绑定事件
        $(".x-dialog-close, .x-dialog-cancel").unbind("click");
        $(".x-dialog-close, .x-dialog-cancel").on("click", function () { hideDialog(); });
      })
    }
  })
  
  // 对话框相关
  function initDialog() {
    // 初始化样式
    $(".x-dialog-background").css({"display":"none", "position":"fixed", "left": "0px", "top": "0px", 
        "width": "100%", "height":"100%", "background-color": "#000", "opacity": 0.5});
    $(".x-dialog-close").css({"background-color":"red", "float":"right", "border":"none"});

    $(".x-dialog").each(function (index, ele) {
        var self = $(ele);
        var width = window.innerWidth;
        if (width < 600) {
          dialogWidth = width - 40;
        } else {
          dialogWidth = 600;
        }
        var left = (width - dialogWidth) / 2;
        self.css({"width":dialogWidth, "left": left});
    });
  }
  
  function hideDialog() {
      $(".x-dialog").hide();
      $(".x-dialog-background").hide();
      $(".x-dialog-remote").remove();// 清空远程的dialog
  }
  
  $(".x-dialog-background").click(function () {
      hideDialog();
  })
  
  $(".x-dialog-close, .x-dialog-cancel").click(function () {
      hideDialog();
  })
  
  function doModal(id) {
    initDialog();
    $(".x-dialog-background").show();
    $(".x-dialog-remote").show();
    $("#"+id).show();
  }

  function initElementProcessors() {
    initSelect();
  }

  initElementProcessors();
};

$(document).ready(function () {
    XUI(window);
})

