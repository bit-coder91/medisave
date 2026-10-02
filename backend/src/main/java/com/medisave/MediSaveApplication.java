package com.medisave;

import com.google.auth.oauth2.GoogleCredentials;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.cloud.FirestoreClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.stream.Collectors;

@SpringBootApplication
public class MediSaveApplication {
    public static void main(String[] a) { SpringApplication.run(MediSaveApplication.class, a); }
}

/** Minimal CSV reader (datasets contain no quoted commas). */
final class Csv {
    static List<Map<String, String>> read(String name) {
        try (var r = new BufferedReader(new InputStreamReader(
                Csv.class.getResourceAsStream("/data/" + name), StandardCharsets.UTF_8))) {
            var head = r.readLine().split(",");
            return r.lines().filter(l -> !l.isBlank()).map(l -> {
                var c = l.split(",", -1); var m = new LinkedHashMap<String, String>();
                for (int i = 0; i < head.length; i++) m.put(head[i], c[i]);
                return m;
            }).collect(Collectors.toList());
        } catch (IOException | NullPointerException e) { throw new IllegalStateException("Cannot read " + name, e); }
    }
}

@Service
class PriceService {
    private final List<Map<String, String>> meds = Csv.read("medicines.csv"),
        shops = Csv.read("pharmacies.csv"), prices = Csv.read("prices.csv");

    List<Map<String, Object>> search(String q, Double lat, Double lng) {
        String s = q.toLowerCase().trim();
        return meds.stream().filter(m -> (m.get("brand") + m.get("generic_name") + m.get("salt")).toLowerCase().contains(s))
            .map(m -> {
                var offers = prices.stream().filter(p -> p.get("med_id").equals(m.get("id"))).map(p -> {
                    var shop = shops.stream().filter(x -> x.get("id").equals(p.get("pharmacy_id"))).findFirst().orElseThrow();
                    var offer = new LinkedHashMap<String, Object>();
                    offer.put("pharmacy", shop.get("name")); offer.put("area", shop.get("area"));
                    offer.put("brand_price", Double.parseDouble(p.get("brand_price")));
                    offer.put("generic_price", Double.parseDouble(p.get("generic_price")));
                    offer.put("km", lat == null || lng == null ? null : round(distance(lat, lng, Double.parseDouble(shop.get("lat")), Double.parseDouble(shop.get("lng"))), 1));
                    return offer;
                }).sorted(Comparator.comparingDouble(o -> lat == null ? (double) o.get("generic_price") : (double) o.get("km"))).toList();
                double bestBrand = offers.stream().mapToDouble(o -> (double) o.get("brand_price")).filter(v -> v > 0).min().orElse(0);
                double bestGen = (double) offers.get(0).get("generic_price");
                double maxBrand = offers.stream().mapToDouble(o -> (double) o.get("brand_price")).max().orElse(bestBrand);
                var result = new LinkedHashMap<String, Object>();
                result.put("id", m.get("id")); result.put("brand", m.get("brand")); result.put("generic_name", m.get("generic_name"));
                result.put("generic_label", m.get("generic_label")); result.put("salt", m.get("salt")); result.put("strength", m.get("strength"));
                result.put("who_gmp", m.get("who_gmp").equals("yes")); result.put("bioequiv_note", m.get("bioequiv_note"));
                result.put("brand_price_spread_pct", round((maxBrand - bestBrand) / maxBrand * 100, 1));
                result.put("cheapest_brand", bestBrand); result.put("cheapest_generic", bestGen);
                result.put("generic_savings_pct", round((1 - bestGen / bestBrand) * 100, 1)); result.put("offers", offers);
                return result;
            }).toList();
    }
    private static double distance(double a, double b, double c, double d) {
        double p = Math.PI / 180, x = Math.pow(Math.sin((c - a) * p / 2), 2) + Math.cos(a * p) * Math.cos(c * p) * Math.pow(Math.sin((d - b) * p / 2), 2);
        return 12742 * Math.asin(Math.sqrt(x));
    }
    private static double round(double value, int decimals) { double factor = Math.pow(10, decimals); return Math.round(value * factor) / factor; }
}

/** Optional Firestore search log; enabled when FIREBASE_CREDENTIALS_JSON is set. */
@Service
class SearchLog {
    private final boolean on;
    SearchLog(@Value("${FIREBASE_CREDENTIALS_JSON:}") String json) throws IOException {
        on = !json.isBlank();
        if (on && FirebaseApp.getApps().isEmpty())
            FirebaseApp.initializeApp(FirebaseOptions.builder().setCredentials(
                GoogleCredentials.fromStream(new ByteArrayInputStream(json.getBytes(StandardCharsets.UTF_8)))).build());
    }
    void log(String q, int hits) {
        if (on) FirestoreClient.getFirestore().collection("searches").add(Map.of("q", q, "hits", hits, "ts", System.currentTimeMillis()));
    }
}

@RestController
@RequestMapping("/api/v1")
@CrossOrigin
class CompareController {
    private final PriceService svc; private final SearchLog log;
    CompareController(PriceService s, SearchLog l) { svc = s; log = l; }

    @GetMapping("/compare")
    Map<String, Object> compare(@RequestParam String q, @RequestParam(required = false) Double lat, @RequestParam(required = false) Double lng) {
        if (q.trim().length() < 2) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "q must be at least 2 characters");
        if ((lat == null) != (lng == null)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "lat and lng must be supplied together");
        var r = svc.search(q, lat, lng); log.log(q, r.size());
        return Map.of("results", r);
    }
}
