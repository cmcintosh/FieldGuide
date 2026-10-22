// SPDX-License-Identifier: GPL-2.0-only
package org.fieldguide.nearby;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.net.wifi.p2p.WifiP2pDevice;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Foreground native transport companion; not the complete RAG/maps Android app. */
@SuppressLint("MissingPermission") // Runtime permission checks wrap every radio action.
public final class MainActivity extends Activity {
    private static final int OPEN=10,SAVE=11,PERMISSIONS=12;
    private final ExecutorService files=Executors.newSingleThreadExecutor();
    private final HashSet<String> bluetoothSeen=new HashSet<>(),wifiSeen=new HashSet<>();
    private NearbyTransfers transfers;
    private NearbyRadios radios;
    private TextView status,outgoingSummary,incomingSummary,hotspotSummary;
    private EditText address,title,message;
    private LinearLayout bluetoothList,wifiList;
    private byte[] outgoing,pending,accepted;
    private Runnable pendingPermissionAction;
    private boolean listenAfterGroup=false;
    private Button acceptButton,rejectButton,exportButton;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ScrollView scroll=new ScrollView(this);LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(24,24,24,32);
        scroll.addView(layout);setContentView(scroll);
        scroll.setOnApplyWindowInsetsListener((view,insets)->{view.setPadding(0,insets.getSystemWindowInsetTop(),0,insets.getSystemWindowInsetBottom());return insets;});
        heading(layout,"FieldGuide Nearby");
        text(layout,"Native Bluetooth, Wi-Fi Direct and local hotspot exchange · development preview 0.3. Keep this screen open during transfer. This companion moves selected-share files; it does not include the LLM or map viewer.");
        status=text(layout,"Choose a selected-share file or compose a field message.");status.setTextIsSelectable(true);
        transfers=new NearbyTransfers(new NearbyTransfers.Listener() {
            public void event(String value) { report(value); }
            public void received(byte[] data,String summary) { String text=new String(data,StandardCharsets.UTF_8);String preview=text.substring(0,Math.min(text.length(),1800));ui(()->{
                pending=data;incomingSummary.setText("Received for review: "+summary+"\n\n"+preview);
                acceptButton.setEnabled(true);rejectButton.setEnabled(true);report("Frame verified. Review before accepting; nothing was imported.");
            }); }
        });
        radios=new NearbyRadios(this,new NearbyRadios.Listener() {
            public void event(String value) { report(value); }
            public void bluetoothPeer(BluetoothDevice device) { ui(()->addBluetooth(device)); }
            public void wifiPeer(WifiP2pDevice device) { ui(()->addWifi(device)); }
            public void wifiGroup(InetAddress owner,boolean isOwner) { ui(()->{
                if(!isOwner && owner!=null)address.setText(owner.getHostAddress());
                report(isOwner?"Wi-Fi Direct group ready. Host addresses: "+localAddresses():"Wi-Fi Direct connected. Tap Send over Wi-Fi when the receiver is listening.");
                if(isOwner && listenAfterGroup) { listenAfterGroup=false;transfers.listenTcp(); }
            }); }
            public void hotspot(String ssid,String password) { ui(()->hotspotSummary.setText(ssid==null||ssid.isEmpty()?"Hotspot stopped.":"Join this local-only Wi-Fi network on the other device:\nSSID: "+ssid+"\nPassword: "+(password==null?"(none)":password)+"\nHost addresses: "+localAddresses())); }
        });

        heading(layout,"1 · Choose what to send");
        outgoingSummary=text(layout,"No outgoing selected-share file loaded.");
        button(layout,"Open selected-share JSON",()->{Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT);intent.setType("*/*");intent.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"application/json","text/plain","application/octet-stream"});intent.addCategory(Intent.CATEGORY_OPENABLE);startActivityForResult(intent,OPEN);});
        title=input(layout,"Message title",false);message=input(layout,"Short field message",true);
        button(layout,"Use message as outgoing document",this::compose);

        heading(layout,"2 · Bluetooth");
        button(layout,"Enable Bluetooth / show paired devices",()->bluetoothAction(false,false,()->{
            if(!bluetoothEnabled())return;bluetoothSeen.clear();bluetoothList.removeAllViews();radios.bluetoothPeers(false);
        }));
        button(layout,"Discover Bluetooth peers",()->bluetoothAction(true,false,()->{
            if(!bluetoothEnabled())return;bluetoothSeen.clear();bluetoothList.removeAllViews();radios.bluetoothPeers(true);
        }));
        button(layout,"Make discoverable for 120 seconds",()->bluetoothAction(false,true,()->{
            if(!bluetoothEnabled())return;Intent discover=new Intent(BluetoothAdapter.ACTION_REQUEST_DISCOVERABLE);discover.putExtra(BluetoothAdapter.EXTRA_DISCOVERABLE_DURATION,120);startActivity(discover);
        }));
        button(layout,"Receive one Bluetooth transfer",()->bluetoothAction(false,false,()->{if(bluetoothEnabled())transfers.listenBluetooth(radios.bluetooth);}));
        bluetoothList=new LinearLayout(this);bluetoothList.setOrientation(LinearLayout.VERTICAL);layout.addView(bluetoothList);

        heading(layout,"3 · Wi-Fi Direct");
        button(layout,"Host Wi-Fi Direct group and receive",()->wifiAction(()->{listenAfterGroup=true;radios.hostWifi();}));
        button(layout,"Discover Wi-Fi Direct peers",()->wifiAction(()->{wifiSeen.clear();wifiList.removeAllViews();radios.discoverWifi();}));
        button(layout,"Disconnect Wi-Fi Direct group",()->wifiAction(()->{listenAfterGroup=false;transfers.cancel();radios.disconnectWifi();}));
        wifiList=new LinearLayout(this);wifiList.setOrientation(LinearLayout.VERTICAL);layout.addView(wifiList);

        heading(layout,"4 · Local-only hotspot / existing Wi-Fi");
        hotspotSummary=text(layout,"No local-only hotspot requested.");hotspotSummary.setTextIsSelectable(true);
        button(layout,"Start local-only hotspot",()->wifiAction(radios::startHotspot));
        button(layout,"Stop local-only hotspot",radios::stopHotspot);
        button(layout,"Show this device's local addresses",()->report(localAddresses()));
        address=input(layout,"Receiver private IPv4 address (no port)",false);address.setInputType(InputType.TYPE_CLASS_PHONE);
        button(layout,"Receive one Wi-Fi/TCP transfer",transfers::listenTcp);
        button(layout,"Send outgoing file over Wi-Fi",()->{if(requireOutgoing())transfers.sendTcp(address.getText().toString(),outgoing.clone());});
        button(layout,"Cancel current transfer",()->{listenAfterGroup=false;transfers.cancel();report("Transfer cancelled.");});

        heading(layout,"5 · Review incoming content");
        incomingSummary=text(layout,"No incoming bundle waiting.");incomingSummary.setTextIsSelectable(true);
        acceptButton=button(layout,"Accept received bundle to app storage",this::accept);
        rejectButton=button(layout,"Reject pending bundle",()->{pending=null;incomingSummary.setText("Pending bundle discarded.");acceptButton.setEnabled(false);rejectButton.setEnabled(false);});
        exportButton=button(layout,"Export last accepted bundle",()->{
            if(accepted==null){report("Accept a received bundle first.");return;}
            Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);intent.setType("application/json");intent.addCategory(Intent.CATEGORY_OPENABLE);intent.putExtra(Intent.EXTRA_TITLE,"fieldguide-received.json");startActivityForResult(intent,SAVE);
        });
        acceptButton.setEnabled(false);rejectButton.setEnabled(false);exportButton.setEnabled(false);
        text(layout,"Export an accepted bundle, then use the Python app's Nearby sharing → Import shared file. FGT1 acknowledges valid frame delivery, not recipient acceptance. Bluetooth uses Android's paired RFCOMM connection; TCP has no application-level authentication or encryption yet. Do not assume a SHA-256 checksum verifies the sender.");
        button(layout,"GPLv2 license / no warranty",()->{
            try(InputStream stream=getAssets().open("LICENSE")){new AlertDialog.Builder(this).setTitle("FieldGuide · GPL-2.0-only · No warranty").setMessage(new String(readLimited(stream),StandardCharsets.UTF_8)).setPositiveButton("Close",null).show();}
            catch(IOException error){report(error.getMessage());}
        });
        files.execute(()->{
            try {
                File previous=new File(getFilesDir(),"outgoing.json");
                if(previous.exists())try(InputStream stream=new FileInputStream(previous)){byte[] data=readLimited(stream);String summary=BundleValidator.validate(data);ui(()->{outgoing=data;outgoingSummary.setText(summary);});}
                File received=new File(getFilesDir(),"received.json");
                if(received.exists())try(InputStream stream=new FileInputStream(received)){byte[] data=readLimited(stream);BundleValidator.validate(data);ui(()->{accepted=data;exportButton.setEnabled(true);});}
            }catch(IOException error){report("Saved bundle could not be loaded: "+error.getMessage());}
        });
    }
    private void ui(Runnable action) { runOnUiThread(()->{if(!isFinishing()&&!isDestroyed())action.run();}); }
    private void report(String value) { ui(()->status.setText(value)); }
    private TextView text(LinearLayout layout,String value) { TextView view=new TextView(this);view.setText(value);view.setPadding(0,10,0,10);layout.addView(view);return view; }
    private void heading(LinearLayout layout,String value) { TextView view=text(layout,value);view.setTextSize(22); }
    private EditText input(LinearLayout layout,String hint,boolean multiline) { EditText view=new EditText(this);view.setHint(hint);view.setContentDescription(hint);view.setSingleLine(!multiline);if(multiline)view.setMinLines(3);layout.addView(view);return view; }
    private Button button(LinearLayout layout,String label,Runnable action) { Button button=new Button(this);button.setText(label);button.setOnClickListener(view->{try{action.run();}catch(RuntimeException error){report("Operation stopped: "+error.getMessage());}});layout.addView(button);return button; }
    private boolean requireOutgoing() { if(outgoing==null){report("Choose an outgoing selected-share file or message first.");return false;}return true; }
    private boolean bluetoothEnabled() {
        if(radios.bluetooth==null){report("Bluetooth unavailable.");return false;}
        if(!radios.bluetooth.isEnabled()){startActivity(new Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE));return false;}return true;
    }
    private void bluetoothAction(boolean scan,boolean advertise,Runnable action) {
        ArrayList<String> needed=new ArrayList<>();
        if(Build.VERSION.SDK_INT>=31){needed.add(Manifest.permission.BLUETOOTH_CONNECT);if(scan)needed.add(Manifest.permission.BLUETOOTH_SCAN);if(advertise)needed.add(Manifest.permission.BLUETOOTH_ADVERTISE);}
        else if(scan)needed.add(Manifest.permission.ACCESS_FINE_LOCATION);
        permissionAction(needed,action);
    }
    private void wifiAction(Runnable action) {
        ArrayList<String> needed=new ArrayList<>();needed.add(Build.VERSION.SDK_INT>=33?Manifest.permission.NEARBY_WIFI_DEVICES:Manifest.permission.ACCESS_FINE_LOCATION);permissionAction(needed,action);
    }
    private void permissionAction(ArrayList<String> needed,Runnable action) {
        needed.removeIf(permission->checkSelfPermission(permission)==PackageManager.PERMISSION_GRANTED);
        if(needed.isEmpty()){action.run();return;}
        pendingPermissionAction=action;requestPermissions(needed.toArray(new String[0]),PERMISSIONS);
    }
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results) {
        super.onRequestPermissionsResult(request,permissions,results);
        if(request!=PERMISSIONS)return;Runnable action=pendingPermissionAction;pendingPermissionAction=null;
        boolean granted=results.length>0;for(int result:results)granted&=result==PackageManager.PERMISSION_GRANTED;
        if(granted&&action!=null){try{action.run();}catch(RuntimeException error){report(error.getMessage());}}
        else report("Permission denied. You can retry the action when ready.");
    }
    private void compose() {
        if(title.getText().toString().trim().isEmpty()||message.getText().toString().trim().isEmpty()){report("Enter a title and message.");return;}
        try {
            JSONObject document=new JSONObject().put("title",title.getText().toString()).put("text",message.getText().toString())
                .put("source","FieldGuide Nearby user entry").put("license","User-provided; rights not verified").put("pack","field-messages").put("updated",Instant.now().toString());
            byte[] data=new JSONObject().put("kind","field-library-share-v1").put("documents",new JSONArray().put(document)).put("waypoints",new JSONArray()).toString().getBytes(StandardCharsets.UTF_8);
            loadOutgoing(data);
        }catch(Exception error){report("Could not create message: "+error.getMessage());}
    }
    private void loadOutgoing(byte[] data) {
        files.execute(()->{
            try {String summary=BundleValidator.validate(data);savePrivate("outgoing.json",data);ui(()->{outgoing=data;outgoingSummary.setText(summary);report("Outgoing bundle ready. Choose a peer to send it.");});}
            catch(IOException error){report(error.getMessage());}
        });
    }
    private void accept() {
        if(pending==null)return;byte[] data=pending.clone();
        files.execute(()->{try{BundleValidator.validate(data);savePrivate("received.json",data);ui(()->{accepted=data;pending=null;acceptButton.setEnabled(false);rejectButton.setEnabled(false);exportButton.setEnabled(true);report("Received bundle accepted to private app storage. Export it to import into the main library.");});}catch(IOException error){report(error.getMessage());}});
    }
    private void savePrivate(String name,byte[] data) throws IOException {
        File temporary=new File(getFilesDir(),name+".tmp");
        try(FileOutputStream stream=new FileOutputStream(temporary)){stream.write(data);stream.getFD().sync();}
        if(!temporary.renameTo(new File(getFilesDir(),name)))throw new IOException("Could not save bundle atomically");
    }
    private static byte[] readLimited(InputStream stream) throws IOException {
        if(stream==null)throw new IOException("Selected file could not be opened");
        ByteArrayOutputStream output=new ByteArrayOutputStream();byte[] block=new byte[32768];int count;
        while((count=stream.read(block))!=-1){if(output.size()+count>FrameCodec.MAX_BYTES)throw new IOException("Selected file exceeds 7 MB");output.write(block,0,count);}return output.toByteArray();
    }
    @Override protected void onActivityResult(int request,int result,Intent intent) {
        super.onActivityResult(request,result,intent);if(result!=RESULT_OK||intent==null||intent.getData()==null)return;Uri uri=intent.getData();
        if(request==OPEN)files.execute(()->{try(InputStream stream=getContentResolver().openInputStream(uri)){loadOutgoing(readLimited(stream));}catch(IOException error){report(error.getMessage());}});
        else if(request==SAVE && accepted!=null){byte[] data=accepted.clone();files.execute(()->{try(OutputStream stream=getContentResolver().openOutputStream(uri,"w")){if(stream==null)throw new IOException("Cannot open destination");stream.write(data);report("Accepted bundle exported. Import it with the Python app's Nearby sharing tab.");}catch(IOException error){report(error.getMessage());}});}
    }
    private void addBluetooth(BluetoothDevice device) {
        try {String key=device.getAddress();if(!bluetoothSeen.add(key))return;String name=device.getName();
            button(bluetoothList,"Send to "+(name==null?"Bluetooth device":name)+" · "+key,()->bluetoothAction(true,false,()->{if(requireOutgoing())transfers.sendBluetooth(radios.bluetooth,device,outgoing.clone());}));
        }catch(SecurityException error){report("Bluetooth connect permission is required to list peers.");}
    }
    private void addWifi(WifiP2pDevice device) { if(!wifiSeen.add(device.deviceAddress))return;button(wifiList,"Connect · "+device.deviceName+" · "+device.deviceAddress,()->wifiAction(()->radios.connectWifi(device))); }
    private String localAddresses() {
        ArrayList<String> values=new ArrayList<>();
        try {for(NetworkInterface network:Collections.list(NetworkInterface.getNetworkInterfaces()))for(InetAddress ip:Collections.list(network.getInetAddresses()))
            if(ip instanceof Inet4Address && !ip.isLoopbackAddress() && ip.isSiteLocalAddress())values.add(network.getName()+": "+ip.getHostAddress());}
        catch(Exception error){return "Check Android Wi-Fi settings for the local IP address.";}
        return values.isEmpty()?"No private IPv4 interface yet.":String.join("; ",values);
    }
    @Override protected void onDestroy() { if(transfers!=null)transfers.close();if(radios!=null)radios.close();files.shutdownNow();super.onDestroy(); }
}
