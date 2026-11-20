import QtQuick
import QtQuick.Window

Rectangle {
    id: debugRoot
    anchors.fill: parent
    color: "#261A1F2B"
    border.color: "#00FF99"
    border.width: 2

    Component.onCompleted: {
        console.log("[插件] 调试层：加载成功")
    }

    Component.onDestruction: {
        console.log("[插件] 调试层：正在卸载/销毁")
    }
    
    Canvas {
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d");
            var w = parent.width;
            var h = parent.height;
            var margin = 24;
            var pixelsPerCm = Screen.pixelDensity > 0 ? Screen.pixelDensity * 10 : 37.795;
            var stepPx = pixelsPerCm / 10;
            var majorPx = pixelsPerCm;

            ctx.clearRect(0, 0, w, h);

            ctx.strokeStyle = "rgba(0, 255, 153, 0.18)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            var maxCmX = Math.floor((w - 2 * margin) / majorPx);
            var maxCmY = Math.floor((h - 2 * margin) / majorPx);
            for (var cmx = 0; cmx <= maxCmX; cmx++) {
                var gx = margin + cmx * majorPx;
                ctx.moveTo(gx, margin);
                ctx.lineTo(gx, h - margin);
            }
            for (var cmy = 0; cmy <= maxCmY; cmy++) {
                var gy = margin + cmy * majorPx;
                ctx.moveTo(margin, gy);
                ctx.lineTo(w - margin, gy);
            }
            ctx.stroke();

            ctx.strokeStyle = "rgba(0, 255, 153, 0.55)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            var maxMmX = Math.floor((w - 2 * margin) / stepPx);
            var maxMmY = Math.floor((h - 2 * margin) / stepPx);
            for (var i = 0; i <= maxMmX; i++) {
                var x = margin + i * stepPx;
                var tick = i % 10 === 0 ? 10 : 5;
                ctx.moveTo(x, margin);
                ctx.lineTo(x, margin - tick);
                ctx.moveTo(x, h - margin);
                ctx.lineTo(x, h - margin + tick);
            }
            for (var j = 0; j <= maxMmY; j++) {
                var y = margin + j * stepPx;
                var tickY = j % 10 === 0 ? 10 : 5;
                ctx.moveTo(margin, y);
                ctx.lineTo(margin - tickY, y);
                ctx.moveTo(w - margin, y);
                ctx.lineTo(w - margin + tickY, y);
            }
            ctx.stroke();

            ctx.fillStyle = "rgba(138, 252, 215, 0.9)";
            ctx.font = "12px sans-serif";
            ctx.textBaseline = "middle";
            ctx.textAlign = "center";
            for (var cx = 0; cx <= maxCmX; cx++) {
                var labelX = margin + cx * majorPx;
                var textX = cx + "cm";
                ctx.fillText(textX, labelX, margin - 14);
                ctx.fillText(textX, labelX, h - margin + 14);
            }
            ctx.textAlign = "right";
            for (var cy = 0; cy <= maxCmY; cy++) {
                var labelY = margin + cy * majorPx;
                var textY = cy + "cm";
                ctx.fillText(textY, margin - 8, labelY);
            }
            ctx.textAlign = "left";
            for (var cy2 = 0; cy2 <= maxCmY; cy2++) {
                var labelY2 = margin + cy2 * majorPx;
                var textY2 = cy2 + "cm";
                ctx.fillText(textY2, w - margin + 8, labelY2);
            }

            ctx.strokeStyle = "rgba(0, 255, 153, 0.8)";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(w / 2, margin);
            ctx.lineTo(w / 2, h - margin);
            ctx.moveTo(margin, h / 2);
            ctx.lineTo(w - margin, h / 2);
            ctx.stroke();
        }
    }
}
