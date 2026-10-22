// SPDX-License-Identifier: GPL-2.0-only
package org.fieldguide.nearby;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;

/** Shared FGT1 wire framing. Integrity does not establish sender identity. */
public final class FrameCodec {
    public static final int MAX_BYTES = 7_000_000;
    public static final int PORT = 43721;
    private static final byte[] MAGIC = {'F','G','T','1'};
    private FrameCodec() {}

    private static byte[] digest(byte[] data) throws IOException {
        try { return MessageDigest.getInstance("SHA-256").digest(data); }
        catch (NoSuchAlgorithmException error) { throw new IOException("SHA-256 unavailable", error); }
    }

    public static void write(OutputStream output, byte[] data) throws IOException {
        if (data.length == 0 || data.length > MAX_BYTES) throw new IOException("Transfer exceeds 7 MB limit");
        DataOutputStream stream = new DataOutputStream(output);
        stream.write(MAGIC); stream.writeInt(data.length); stream.write(digest(data));
        for (int offset=0; offset<data.length; offset+=65536) {
            stream.write(data, offset, Math.min(65536, data.length-offset));
        }
        stream.flush();
    }

    public static byte[] read(InputStream input) throws IOException {
        DataInputStream stream = new DataInputStream(input);
        byte[] magic = new byte[4]; stream.readFully(magic);
        if (!Arrays.equals(magic,MAGIC)) throw new IOException("Unsupported transfer protocol");
        int size = stream.readInt();
        if (size<=0 || size>MAX_BYTES) throw new IOException("Declared size exceeds 7 MB limit");
        byte[] expected = new byte[32]; stream.readFully(expected);
        byte[] data = new byte[size]; stream.readFully(data);
        if (!MessageDigest.isEqual(expected,digest(data))) throw new IOException("Transfer checksum failed");
        return data;
    }
}
