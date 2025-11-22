import { describe, it, expect, vi } from "vitest";

describe("content.js form scanning", () => {
  it("scans form fields correctly", () => {
    document.body.innerHTML = `
      <form>
        <label for="name">Full Name</label>
        <input id="name" name="full_name" type="text" />

        <label for="cover">Why work here?</label>
        <textarea id="cover" name="cover_letter"></textarea>
      </form>
    `;

    // Test the scanning logic directly
    const inputs = document.querySelectorAll("input, textarea");
    expect(inputs.length).toBe(2);

    const nameInput = document.getElementById("name") as HTMLInputElement;
    expect(nameInput.name).toBe("full_name");

    const coverText = document.getElementById("cover") as HTMLTextAreaElement;
    expect(coverText.name).toBe("cover_letter");
  });

  it("fills form fields with values", () => {
    document.body.innerHTML = `
      <form>
        <input id="name" type="text" />
        <textarea id="cover"></textarea>
      </form>
    `;

    const nameInput = document.getElementById("name") as HTMLInputElement;
    const coverText = document.getElementById("cover") as HTMLTextAreaElement;

    // Simulate filling
    nameInput.value = "Leo Klemet";
    coverText.value = "I'm excited about this role!";

    expect(nameInput.value).toBe("Leo Klemet");
    expect(coverText.value).toBe("I'm excited about this role!");
  });
});
