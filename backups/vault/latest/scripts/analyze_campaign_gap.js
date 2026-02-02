/**
 * Campaign Gap Analysis Script
 * 
 * Objective: Compare Chuffed campaigns (Source) against Whydonate campaigns (Target)
 * to identify which campaigns still need to be migrated.
 * 
 * Usage: node scripts/analyze_campaign_gap.js
 */

const fs = require('fs');
const path = require('path');

// Helper to normalize strings for comparison (slugify)
function normalize(str) {
    if (!str) return '';
    return str.toLowerCase()
        .trim()
        .replace(/[^\w\s-]/g, '') // Remove non-word chars
        .replace(/[\s_-]+/g, '-') // Replace spaces/underscores with hyphens
        .replace(/^-+|-+$/g, ''); // Trim hyphens
}

// Helper to calculate similarity (Levenshtein distance usually, but simple containment for now)
function isSimilar(title1, title2) {
    const s1 = normalize(title1);
    const s2 = normalize(title2);
    return s1 === s2 || s1.includes(s2) || s2.includes(s1);
}

const CHUFFED_FILE = path.join(__dirname, '../data/chuffed_campaigns.json');
const WHYDONATE_FILE = path.join(__dirname, '../data/whydonate_campaigns.json');
const OUTPUT_FILE = path.join(__dirname, '../data/migration_todo.json');

function main() {
    try {
        // Load Data
        console.log('Loading campaign data...');

        if (!fs.existsSync(CHUFFED_FILE) || !fs.existsSync(WHYDONATE_FILE)) {
            console.error('Error: Input files not found.');
            console.error(`Please ensure ${CHUFFED_FILE} and ${WHYDONATE_FILE} exist.`);
            process.exit(1);
        }

        const chuffedData = JSON.parse(fs.readFileSync(CHUFFED_FILE, 'utf8'));
        const whydonateData = JSON.parse(fs.readFileSync(WHYDONATE_FILE, 'utf8'));

        console.log(`Loaded ${chuffedData.length} Chuffed campaigns.`);
        console.log(`Loaded ${whydonateData.length} Whydonate campaigns.`);

        const toMigrate = [];
        const alreadyMigrated = [];

        // Analysis Loop
        chuffedData.forEach(chuffedOption => {
            const match = whydonateData.find(wd => isSimilar(chuffedOption.title, wd.title));

            if (match) {
                alreadyMigrated.push({
                    chuffed: chuffedOption,
                    whydonate: match
                });
            } else {
                toMigrate.push(chuffedOption);
            }
        });

        // Report
        console.log('\n--- Analysis Report ---');
        console.log(`Total Chuffed Campaigns: ${chuffedData.length}`);
        console.log(`Already on Whydonate:    ${alreadyMigrated.length}`);
        console.log(`Need Migration:          ${toMigrate.length}`);

        // Save Results
        fs.writeFileSync(OUTPUT_FILE, JSON.stringify(toMigrate, null, 2));
        console.log(`\nMigration list saved to: ${OUTPUT_FILE}`);

    } catch (error) {
        console.error('An error occurred:', error);
    }
}

main();
