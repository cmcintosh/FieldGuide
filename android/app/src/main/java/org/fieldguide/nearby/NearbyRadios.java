// SPDX-License-Identifier: GPL-2.0-only
package org.fieldguide.nearby;

import android.Manifest;
import android.annotation.SuppressLint;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.wifi.WifiManager;
import android.net.wifi.p2p.WifiP2pConfig;
import android.net.wifi.p2p.WifiP2pDevice;
import android.net.wifi.p2p.WifiP2pManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import java.io.Closeable;
import java.net.InetAddress;

/** Native discovery/group/hotspot operations. No silent radio enablement. */
@SuppressLint("MissingPermission") // Invoked by MainActivity after per-action permission checks.
public final class NearbyRadios implements Closeable {
    public interface Listener {
        void event(String message);
        void bluetoothPeer(BluetoothDevice device);
        void wifiPeer(WifiP2pDevice device);
        void wifiGroup(InetAddress owner,boolean isOwner);
        void hotspot(String ssid,String password);
    }
    private final Context context;
    private final Listener listener;
    public final BluetoothAdapter bluetooth;
    private final WifiManager wifi;
    private final WifiP2pManager p2p;
    private WifiP2pManager.Channel channel;
    private WifiManager.LocalOnlyHotspotReservation hotspot;
    private boolean wifiRequested=false,ownGroup=false,closed=false;

    public NearbyRadios(Context context,Listener listener) {
        this.context=context;this.listener=listener;
        BluetoothManager manager=context.getSystemService(BluetoothManager.class);
        bluetooth=manager==null?null:manager.getAdapter();
        wifi=context.getApplicationContext().getSystemService(WifiManager.class);
        p2p=context.getSystemService(WifiP2pManager.class);
        if(p2p!=null) channel=p2p.initialize(context,Looper.getMainLooper(),()->listener.event("Wi-Fi Direct channel closed; reopen this screen."));
        IntentFilter filter=new IntentFilter();
        filter.addAction(BluetoothDevice.ACTION_FOUND);filter.addAction(BluetoothAdapter.ACTION_DISCOVERY_FINISHED);
        filter.addAction(WifiP2pManager.WIFI_P2P_PEERS_CHANGED_ACTION);filter.addAction(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION);
        filter.addAction(WifiP2pManager.WIFI_P2P_STATE_CHANGED_ACTION);
        if(Build.VERSION.SDK_INT>=33) context.registerReceiver(receiver,filter,Context.RECEIVER_EXPORTED);
        else context.registerReceiver(receiver,filter);
    }
    private final BroadcastReceiver receiver=new BroadcastReceiver() {
        @Override public void onReceive(Context context,Intent intent) {
            if(closed) return;
            try {
                String action=intent.getAction();
                if(BluetoothDevice.ACTION_FOUND.equals(action)) {
                    if(Build.VERSION.SDK_INT>=31 && context.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)!=PackageManager.PERMISSION_GRANTED) return;
                    BluetoothDevice device=Build.VERSION.SDK_INT>=33?intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE,BluetoothDevice.class):intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE);
                    if(device!=null) listener.bluetoothPeer(device);
                } else if(BluetoothAdapter.ACTION_DISCOVERY_FINISHED.equals(action)) listener.event("Bluetooth discovery finished.");
                else if(wifiRequested && p2p!=null && channel!=null) {
                    if(WifiP2pManager.WIFI_P2P_PEERS_CHANGED_ACTION.equals(action))
                        p2p.requestPeers(channel,peers->{for(WifiP2pDevice device:peers.getDeviceList())listener.wifiPeer(device);});
                    else if(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION.equals(action)) requestGroupInfo();
                    else if(WifiP2pManager.WIFI_P2P_STATE_CHANGED_ACTION.equals(action)) listener.event("Wi-Fi Direct state changed.");
                }
            } catch(SecurityException error) { listener.event("Nearby permission changed; grant it again before retrying."); }
        }
    };
    public void bluetoothPeers(boolean scan) {
        if(bluetooth==null) { listener.event("Bluetooth is unavailable on this device.");return; }
        if(!bluetooth.isEnabled()) { listener.event("Enable Bluetooth using the system prompt first.");return; }
        for(BluetoothDevice device:bluetooth.getBondedDevices())listener.bluetoothPeer(device);
        if(scan) { bluetooth.cancelDiscovery();listener.event(bluetooth.startDiscovery()?"Discovering nearby Bluetooth devices…":"Bluetooth discovery could not start."); }
    }
    private WifiP2pManager.ActionListener action(String operation) {
        return new WifiP2pManager.ActionListener() {
            public void onSuccess() { listener.event(operation+" requested; waiting for Android's connection result."); }
            public void onFailure(int reason) { listener.event(operation+" failed (Android reason "+reason+"). Check Wi-Fi, nearby permissions and location settings on older devices."); }
        };
    }
    private boolean available() {
        if(p2p==null || channel==null) { listener.event("Wi-Fi Direct is unavailable on this device.");return false; }
        wifiRequested=true;return true;
    }
    public void discoverWifi() { if(available()) p2p.discoverPeers(channel,action("Wi-Fi Direct discovery")); }
    public void hostWifi() {
        if(!available())return;
        p2p.createGroup(channel,new WifiP2pManager.ActionListener() {
            public void onSuccess() { ownGroup=true;listener.event("Wi-Fi Direct group requested.");requestGroupInfo(); }
            public void onFailure(int reason) { listener.event("Could not create group (reason "+reason+"). Disconnect an existing group and retry."); }
        });
    }
    public void connectWifi(WifiP2pDevice device) {
        if(!available())return;
        WifiP2pConfig config=new WifiP2pConfig();config.deviceAddress=device.deviceAddress;
        p2p.connect(channel,config,action("Wi-Fi Direct connection"));
    }
    private void requestGroupInfo() {
        if(closed || p2p==null || channel==null)return;
        p2p.requestConnectionInfo(channel,info->{if(!closed && info.groupFormed)listener.wifiGroup(info.groupOwnerAddress,info.isGroupOwner);});
    }
    public void disconnectWifi() {
        if(p2p!=null && channel!=null) {
            p2p.cancelConnect(channel,action("Cancel connection"));p2p.removeGroup(channel,action("Remove group"));
        }
        ownGroup=false;
    }
    public void startHotspot() {
        if(wifi==null) { listener.event("Wi-Fi is unavailable.");return; }
        if(hotspot!=null) { listener.event("A local-only hotspot is already running.");return; }
        listener.event("Requesting a local-only hotspot…");
        wifi.startLocalOnlyHotspot(new WifiManager.LocalOnlyHotspotCallback() {
            @Override public void onStarted(WifiManager.LocalOnlyHotspotReservation reservation) {
                if(closed) { reservation.close();return; }
                hotspot=reservation;
                if(Build.VERSION.SDK_INT>=30) listener.hotspot(reservation.getSoftApConfiguration().getSsid(),reservation.getSoftApConfiguration().getPassphrase());
                else { android.net.wifi.WifiConfiguration config=reservation.getWifiConfiguration();listener.hotspot(config.SSID,config.preSharedKey); }
            }
            @Override public void onStopped() { hotspot=null;if(!closed)listener.hotspot("",""); }
            @Override public void onFailed(int reason) { if(!closed)listener.event("Local-only hotspot failed (reason "+reason+"). It may conflict with an active Wi-Fi Direct group."); }
        },new Handler(Looper.getMainLooper()));
    }
    public void stopHotspot() { if(hotspot!=null){hotspot.close();hotspot=null;}listener.hotspot("",""); }
    @Override public void close() {
        closed=true;stopHotspot();
        try { if(bluetooth!=null && (Build.VERSION.SDK_INT<31 || context.checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN)==PackageManager.PERMISSION_GRANTED)) bluetooth.cancelDiscovery(); } catch(SecurityException ignored) {}
        try { if(ownGroup && p2p!=null && channel!=null)p2p.removeGroup(channel,null); } catch(SecurityException ignored) {}
        context.unregisterReceiver(receiver);if(channel!=null && Build.VERSION.SDK_INT>=27)channel.close();
    }
}
