// SPDX-License-Identifier: GPL-2.0-only
import org.fieldguide.nearby.FrameCodec;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** Android-independent interoperability tests, run with JDK 17 in CI. */
public final class FrameCodecSelfTest {
    private interface Check {void run() throws IOException;}
    private static void rejects(Check check) throws IOException {
        try {check.run();throw new AssertionError("Invalid frame was accepted");}catch(IOException expected){}
    }
    public static void main(String[] args) throws Exception {
        byte[] data=Files.readAllBytes(Path.of(args[0]));
        String hex=Files.readString(Path.of(args[1])).trim();
        byte[] expected=new byte[hex.length()/2];
        for(int i=0;i<expected.length;i++)expected[i]=(byte)Integer.parseInt(hex.substring(i*2,i*2+2),16);
        ByteArrayOutputStream encoded=new ByteArrayOutputStream();FrameCodec.write(encoded,data);
        if(!Arrays.equals(encoded.toByteArray(),expected))throw new AssertionError("Python/Java golden frames differ");
        if(!Arrays.equals(FrameCodec.read(new ByteArrayInputStream(expected)),data))throw new AssertionError("Payload differs");
        byte[] bad=expected.clone();bad[39]^=1;rejects(()->FrameCodec.read(new ByteArrayInputStream(bad)));
        rejects(()->FrameCodec.read(new ByteArrayInputStream(Arrays.copyOf(expected,expected.length-1))));
        byte[] huge=expected.clone();Arrays.fill(huge,4,8,(byte)127);rejects(()->FrameCodec.read(new ByteArrayInputStream(huge)));
        rejects(()->FrameCodec.write(new ByteArrayOutputStream(),new byte[0]));
        byte[] wrong=expected.clone();wrong[0]='X';rejects(()->FrameCodec.read(new ByteArrayInputStream(wrong)));
        System.out.println("PASS: Java/Python frame compatibility, corruption, truncation, size and protocol rejection");
    }
}
