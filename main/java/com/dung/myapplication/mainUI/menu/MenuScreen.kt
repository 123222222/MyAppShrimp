package com.dung.myapplication.mainUI.menu

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.dung.myapplication.mainUI.common.MyBottomBar
import com.dung.myapplication.mainUI.common.MyTopBar

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MenuScreen(
    onHomeClick: () -> Unit = {},
    onMenuClick: () -> Unit = {},
    onGalleryClick: () -> Unit = {},
    onProfileClick: () -> Unit = {},
    onLogoutClick: () -> Unit = {}
) {
    Scaffold(
        topBar = { MyTopBar("Menu") },
        bottomBar = {
            MyBottomBar(
                onHomeClick = onHomeClick,
                onMenuClick = onMenuClick,
                onGalleryClick = onGalleryClick,
                onProfileClick = onProfileClick,
                onLogoutClick = onLogoutClick
            )
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            // Menu content - empty
        }
    }
}
