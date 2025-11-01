package com.dung.myapplication.mainUI

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.dung.myapplication.mainUI.home.HomeScreen
import com.dung.myapplication.mainUI.logout.LogoutScreen
import com.dung.myapplication.mainUI.menu.MenuScreen
import com.dung.myapplication.mainUI.profile.ProfileScreen
import com.dung.myapplication.mainUI.home.CameraStreamScreen
import com.dung.myapplication.mainUI.gallery.GalleryScreen
import com.dung.myapplication.mainUI.gallery.ImageDetailScreen
import androidx.navigation.toRoute

@Composable
fun NavGraph(
    navController: NavHostController,
    modifier: Modifier = Modifier
) {
    NavHost(
        navController = navController,
        startDestination = Home,
        modifier = modifier
    ) {
        // 🏠 Home
        composable<Home> {
            HomeScreen(
                onHomeClick = { /* đang ở Home */ },
                onMenuClick = { navController.navigate(Menu) },
                onGalleryClick = { navController.navigate(Gallery) },
                onProfileClick = { navController.navigate(Profile) },
                onLogoutClick = { navController.navigate(Logout) },
                onDeviceSelected = { streamUrl: String ->  // ✅ Thêm kiểu dữ liệu String
                    navController.navigate(CameraStream(streamUrl))
                }
            )
        }

        // 📋 Menu
        composable<Menu> {
            MenuScreen(
                onHomeClick = { navController.navigate(Home) },
                onMenuClick = { /* đang ở Menu */ },
                onGalleryClick = { navController.navigate(Gallery) },
                onProfileClick = { navController.navigate(Profile) },
                onLogoutClick = { navController.navigate(Logout) }
            )
        }

        // 👤 Profile
        composable<Profile> {
            ProfileScreen(
                onHomeClick = { navController.navigate(Home) },
                onMenuClick = { navController.navigate(Menu) },
                onGalleryClick = { navController.navigate(Gallery) },
                onProfileClick = { /* đang ở Profile */ },
                onLogoutClick = { navController.navigate(Logout) }
            )
        }

        // 🚪 Logout
        composable<Logout> {
            val context = LocalContext.current
            LogoutScreen(
                context = context,
                onCancel = { navController.navigate(Home) }
            )
        }

        // 📹 Camera Stream
        composable<CameraStream> { backStackEntry ->
            val args = backStackEntry.toRoute<CameraStream>()
            CameraStreamScreen(
                streamUrl = args.streamUrl,
                onBackClick = { navController.navigateUp() },
                onHomeClick = { navController.navigate(Home) },
                onMenuClick = { navController.navigate(Menu) },
                onGalleryClick = { navController.navigate(Gallery) },
                onProfileClick = { navController.navigate(Profile) },
                onLogoutClick = { navController.navigate(Logout) }
            )
        }

        // 🖼️ Gallery
        composable<Gallery> {
            GalleryScreen(
                onHomeClick = { navController.navigate(Home) },
                onMenuClick = { navController.navigate(Menu) },
                onGalleryClick = { /* đang ở Gallery */ },
                onProfileClick = { navController.navigate(Profile) },
                onLogoutClick = { navController.navigate(Logout) },
                onImageClick = { imageId -> navController.navigate(ImageDetail(imageId)) }
            )
        }

        // 🔍 Image Detail
        composable<ImageDetail> { backStackEntry ->
            val args = backStackEntry.toRoute<ImageDetail>()
            ImageDetailScreen(
                imageId = args.imageId,
                onBackClick = { navController.navigateUp() }
            )
        }
    }
}
