// SPDX-License-Identifier: GPL-2.0-only
package org.fieldguide.nearby;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;

public final class BundleValidator {
    private BundleValidator() {}
    public static String validate(byte[] data) throws IOException {
        if (data.length==0 || data.length>FrameCodec.MAX_BYTES) throw new IOException("Bundle must be under 7 MB");
        try {
            String text=StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(data)).toString();
            JSONObject root=new JSONObject(text);
            if (!"field-library-share-v1".equals(root.optString("kind"))) throw new IOException("Choose an exported FieldGuide selected-share file");
            JSONArray documents=root.has("documents")?root.getJSONArray("documents"):new JSONArray();
            JSONArray points=root.has("waypoints")?root.getJSONArray("waypoints"):new JSONArray();
            int count=documents.length()+points.length();
            if (count<1 || count>1000) throw new IOException("Choose 1–1,000 selected records");
            for (int i=0;i<documents.length();i++) {
                JSONObject item=documents.getJSONObject(i);
                Object title=item.get("title"), body=item.get("text");
                if (!(title instanceof String) || !(body instanceof String) || ((String)title).trim().isEmpty()
                    || ((String)body).trim().isEmpty() || ((String)body).length()>2_000_000) throw new IOException("Invalid document record");
            }
            for (int i=0;i<points.length();i++) {
                JSONObject item=points.getJSONObject(i);
                double lat=item.getDouble("latitude"),lon=item.getDouble("longitude");
                if (item.getString("name").trim().isEmpty() || !Double.isFinite(lat) || !Double.isFinite(lon)
                    || lat< -90 || lat>90 || lon< -180 || lon>180) throw new IOException("Invalid waypoint record");
            }
            return documents.length()+" documents, "+points.length()+" waypoints · "+data.length+" bytes";
        } catch (JSONException | CharacterCodingException error) { throw new IOException("Invalid selected-share JSON",error); }
    }
}
