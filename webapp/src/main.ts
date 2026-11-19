import { defineNginxUIPlugin, registerPlugin } from '@nginxui/plugin-sdk'
import { PLUGIN_ID, setPluginHttpClient, type HttpClientLike } from './api/client'
import AddIpView from './views/AddIpView.vue'
import DashboardView from './views/DashboardView.vue'
import IpListView from './views/IpListView.vue'
import ReportsView from './views/ReportsView.vue'

registerPlugin(
  PLUGIN_ID,
  defineNginxUIPlugin({
    setup(registry) {
      if ('http' in registry && registry.http) {
        setPluginHttpClient(registry.http as unknown as HttpClientLike)
      }

      registry.registerRoute(
        {
          path: 'public-ip-inventory',
          name: 'PublicIpInventory',
          redirect: '/public-ip-inventory/dashboard',
          meta: {
            title: 'Public IP Inventory',
            icon: 'i-ant-design:global-outlined',
          },
          children: [
            {
              path: 'dashboard',
              name: 'PublicIpInventoryDashboard',
              component: DashboardView,
              meta: {
                title: 'Dashboard',
                icon: 'i-ant-design:dashboard-outlined',
              },
            },
            {
              path: 'list',
              name: 'PublicIpInventoryList',
              component: IpListView,
              meta: {
                title: 'IP Address List',
                icon: 'i-ant-design:unordered-list-outlined',
              },
            },
            {
              path: 'add',
              name: 'PublicIpInventoryAdd',
              component: AddIpView,
              meta: {
                title: 'Add IP Address',
                icon: 'i-ant-design:plus-circle-outlined',
              },
            },
            {
              path: 'reports',
              name: 'PublicIpInventoryReports',
              component: ReportsView,
              meta: {
                title: 'Reports',
                icon: 'i-ant-design:file-excel-outlined',
              },
            },
          ],
        },
        { order: 50 },
      )
    },
    teardown() {
      setPluginHttpClient(null)
    },
  }),
)
