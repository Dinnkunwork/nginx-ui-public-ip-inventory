import { defineNginxUIPlugin, registerPlugin, useShared } from '@nginxui/plugin-sdk'
import { PLUGIN_ID, setPluginHttpClient, type HttpClientLike } from './api/client'
import DashboardView from './views/DashboardView.vue'
import IpListView from './views/IpListView.vue'

registerPlugin(
  PLUGIN_ID,
  defineNginxUIPlugin({
    setup(registry) {
      if ('http' in registry && registry.http) {
        setPluginHttpClient(registry.http as unknown as HttpClientLike)
      }

      const sharedIcons = (useShared().antdvIcons ?? {}) as Record<string, unknown>
      const icon = sharedIcons.GlobalOutlined

      registry.registerRoute(
        {
          path: 'public-ip-inventory',
          name: 'PublicIpInventory',
          redirect: '/public-ip-inventory/dashboard',
          meta: {
            name: () => 'Public IP Inventory',
            icon,
          },
        },
        { order: 50 },
      )

      registry.registerRoute(
        {
          path: 'public-ip-inventory/dashboard',
          name: 'PublicIpInventoryDashboard',
          component: DashboardView,
          meta: {
            name: () => 'Dashboard & Reports',
            lastRouteName: 'PublicIpInventory',
          },
        },
        { parent: 'PublicIpInventory', order: 10 },
      )

      registry.registerRoute(
        {
          path: 'public-ip-inventory/list',
          name: 'PublicIpInventoryList',
          component: IpListView,
          meta: {
            name: () => 'IP Address List',
            lastRouteName: 'PublicIpInventory',
          },
        },
        { parent: 'PublicIpInventory', order: 20 },
      )
    },
    teardown() {
      setPluginHttpClient(null)
    },
  }),
)
