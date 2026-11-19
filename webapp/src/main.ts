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
          path: '/public-ip-inventory/dashboard',
          name: 'PublicIpInventoryDashboard',
          component: DashboardView,
          meta: {
            title: 'Dashboard',
            group: 'Public IP Inventory',
            icon: 'i-ant-design:dashboard-outlined',
          },
        },
        { order: 10 },
      )

      registry.registerRoute(
        {
          path: '/public-ip-inventory/list',
          name: 'PublicIpInventoryList',
          component: IpListView,
          meta: {
            title: 'IP Address List',
            group: 'Public IP Inventory',
            icon: 'i-ant-design:unordered-list-outlined',
          },
        },
        { parent: 'PublicIpInventoryDashboard', order: 20 },
      )

      registry.registerRoute(
        {
          path: '/public-ip-inventory/add',
          name: 'PublicIpInventoryAdd',
          component: AddIpView,
          meta: {
            title: 'Add IP Address',
            group: 'Public IP Inventory',
            icon: 'i-ant-design:plus-circle-outlined',
          },
        },
        { parent: 'PublicIpInventoryDashboard', order: 30 },
      )

      registry.registerRoute(
        {
          path: '/public-ip-inventory/reports',
          name: 'PublicIpInventoryReports',
          component: ReportsView,
          meta: {
            title: 'Reports',
            group: 'Public IP Inventory',
            icon: 'i-ant-design:file-excel-outlined',
          },
        },
        { parent: 'PublicIpInventoryDashboard', order: 40 },
      )
    },
    teardown() {
      setPluginHttpClient(null)
    },
  }),
)
