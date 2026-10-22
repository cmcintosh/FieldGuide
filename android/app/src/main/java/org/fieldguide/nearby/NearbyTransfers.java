// SPDX-License-Identifier: GPL-2.0-only
package org.fieldguide.nearby;

import android.annotation.SuppressLint;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothServerSocket;
import android.bluetooth.BluetoothSocket;
import java.io.Closeable;
import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.ArrayList;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/** One explicit operation at a time. Cancellation closes blocking sockets. */
@SuppressLint("MissingPermission") // MainActivity checks the operation's runtime permissions.
public final class NearbyTransfers implements Closeable {
    public static final UUID SERVICE=UUID.fromString("4a78bd94-2c5f-4d4a-9e83-66bda9d78c65");
    public interface Listener { void event(String text); void received(byte[] data,String summary); }
    private interface Task { void run(int generation) throws IOException; }
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final ScheduledExecutorService clock=Executors.newSingleThreadScheduledExecutor();
    private final ArrayList<Closeable> resources=new ArrayList<>();
    private final Listener listener;
    private int generation=0;
    private boolean closed=false;

    public NearbyTransfers(Listener listener) { this.listener=listener; }
    public synchronized void cancel() {
        generation++;
        for(Closeable resource:resources) try { resource.close(); } catch(IOException ignored) {}
        resources.clear();
    }
    private synchronized boolean current(int token) { return token==generation && !closed; }
    private synchronized <T extends Closeable> T track(T resource,int token) throws IOException {
        if(!current(token)) { resource.close(); throw new IOException("Transfer cancelled"); }
        resources.add(resource); return resource;
    }
    private synchronized void start(Task task) {
        if(closed) return;
        cancel(); final int token=generation;
        worker.execute(()->{
            var deadline=clock.schedule(()->{ synchronized(this) {
                if(current(token)) { cancel(); listener.event("Transfer timed out; nothing was imported."); }
            }},180,TimeUnit.SECONDS);
            try { task.run(token); }
            catch(IOException|RuntimeException error) { if(current(token)) listener.event("Transfer stopped: "+error.getMessage()); }
            finally { deadline.cancel(false); synchronized(this) { if(current(token)) cancel(); } }
        });
    }
    private void arrived(byte[] data,int token) throws IOException {
        String summary=BundleValidator.validate(data);
        if(!current(token)) throw new IOException("Transfer cancelled");
        listener.received(data,summary);
    }

    public void listenTcp() {
        start(token->{
            ServerSocket server=track(new ServerSocket(),token);
            server.setReuseAddress(true);server.bind(new InetSocketAddress("0.0.0.0",FrameCodec.PORT));server.setSoTimeout(120000);
            listener.event("Listening for one Wi-Fi/TCP transfer on port "+FrameCodec.PORT+". Keep this app open.");
            Socket socket=track(server.accept(),token);server.close();socket.setSoTimeout(30000);
            byte[] data=FrameCodec.read(socket.getInputStream());BundleValidator.validate(data);
            socket.getOutputStream().write(6);socket.getOutputStream().flush();arrived(data,token);
        });
    }
    public void sendTcp(String address,byte[] data) {
        start(token->{
            BundleValidator.validate(data);
            InetAddress host=privateAddress(address);
            Socket socket=track(new Socket(),token);socket.connect(new InetSocketAddress(host,FrameCodec.PORT),10000);socket.setSoTimeout(30000);
            FrameCodec.write(socket.getOutputStream(),data);
            if(socket.getInputStream().read()!=6) throw new IOException("Receiver did not acknowledge the frame");
            if(current(token)) listener.event("Frame delivered for recipient review; no automatic import.");
        });
    }
    public void listenBluetooth(BluetoothAdapter adapter) {
        start(token->{
            if(adapter==null || !adapter.isEnabled()) throw new IOException("Enable Bluetooth first");
            BluetoothServerSocket server=track(adapter.listenUsingRfcommWithServiceRecord("FieldGuide",SERVICE),token);
            listener.event("Listening for one paired Bluetooth transfer. Use Make discoverable if needed.");
            BluetoothSocket socket=track(server.accept(120000),token);server.close();
            byte[] data=FrameCodec.read(socket.getInputStream());BundleValidator.validate(data);
            socket.getOutputStream().write(6);socket.getOutputStream().flush();arrived(data,token);
        });
    }
    public void sendBluetooth(BluetoothAdapter adapter,BluetoothDevice device,byte[] data) {
        start(token->{
            BundleValidator.validate(data);
            if(adapter==null || !adapter.isEnabled()) throw new IOException("Enable Bluetooth first");
            adapter.cancelDiscovery();
            BluetoothSocket socket=track(device.createRfcommSocketToServiceRecord(SERVICE),token);
            listener.event("Connecting over Bluetooth. Complete Android's pairing dialog if shown.");
            socket.connect();FrameCodec.write(socket.getOutputStream(),data);
            if(socket.getInputStream().read()!=6) throw new IOException("Receiver did not acknowledge the frame");
            if(current(token)) listener.event("Bluetooth frame delivered for recipient review.");
        });
    }
    static InetAddress privateAddress(String input) throws IOException {
        String[] pieces=input.trim().split("\\.",-1);
        if(pieces.length!=4) throw new IOException("Enter the peer's numeric private IPv4 address");
        byte[] bytes=new byte[4];int[] parts=new int[4];
        for(int i=0;i<4;i++) {
            if(!pieces[i].matches("[0-9]{1,3}")) throw new IOException("Invalid IPv4 address");
            parts[i]=Integer.parseInt(pieces[i]);if(parts[i]>255) throw new IOException("Invalid IPv4 address");bytes[i]=(byte)parts[i];
        }
        if(!(parts[0]==10 || parts[0]==127 || (parts[0]==172 && parts[1]>=16 && parts[1]<=31) || (parts[0]==192 && parts[1]==168)))
            throw new IOException("Only private IPv4 peers are supported");
        return InetAddress.getByAddress(bytes);
    }
    @Override public synchronized void close() { cancel();closed=true;worker.shutdownNow();clock.shutdownNow(); }
}
