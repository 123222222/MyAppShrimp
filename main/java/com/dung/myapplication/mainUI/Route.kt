package com.dung.myapplication.mainUI

import kotlinx.serialization.Serializable

@Serializable
object Home

@Serializable
object Logout


@Serializable
object Profile

@Serializable
object Menu

@Serializable
object Gallery

// ➕ Thêm route mới cho màn hình chi tiết thiết bị
@Serializable
object DeviceDetail

// ➕ Thêm route cho Camera Stream
@Serializable
data class CameraStream(val streamUrl: String)

// ➕ Thêm route cho Image Detail
@Serializable
data class ImageDetail(val imageId: String)
