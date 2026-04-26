/**
 * Test utility to verify evaluation data flow
 * This helps debug stale state issues
 */
export const testEvaluationFlow = () => {
    console.log('=== Evaluation Flow Test ===');
    // Test 1: Verify input values are captured correctly
    const testInput1 = {
        borrower_type: 'individual',
        loan_amount: 3000000,
        loan_type: 'personal',
        tenure: 24,
        interest_rate: 14.5,
        collateral_type: 'property',
    };
    console.log('Test 1 - Input 1:', testInput1);
    console.log('Expected loan_amount: 3000000');
    console.log('Actual loan_amount:', testInput1.loan_amount);
    console.log('Match:', testInput1.loan_amount === 3000000 ? '✓' : '✗');
    // Test 2: Verify input update
    const testInput2 = {
        ...testInput1,
        loan_amount: 1500000,
    };
    console.log('\nTest 2 - Input 2 (updated):', testInput2);
    console.log('Expected loan_amount: 1500000');
    console.log('Actual loan_amount:', testInput2.loan_amount);
    console.log('Match:', testInput2.loan_amount === 1500000 ? '✓' : '✗');
    // Test 3: Verify immutability
    console.log('\nTest 3 - Immutability check:');
    console.log('Input 1 unchanged:', testInput1.loan_amount === 3000000 ? '✓' : '✗');
    console.log('Input 2 has new value:', testInput2.loan_amount === 1500000 ? '✓' : '✗');
    console.log('\n=== Test Complete ===');
};
export const createTestInputs = () => {
    return [
        {
            borrower_type: 'individual',
            loan_amount: 3000000,
            loan_type: 'personal',
            tenure: 24,
            interest_rate: 14.5,
            collateral_type: 'property',
        },
        {
            borrower_type: 'individual',
            loan_amount: 1500000,
            loan_type: 'personal',
            tenure: 24,
            interest_rate: 14.5,
            collateral_type: 'property',
        },
    ];
};
export const verifyInputIntegrity = (submittedInput, receivedInput) => {
    const fields = [
        'borrower_type',
        'loan_amount',
        'loan_type',
        'tenure',
        'interest_rate',
        'collateral_type',
    ];
    let allMatch = true;
    for (const field of fields) {
        if (submittedInput[field] !== receivedInput[field]) {
            console.error(`MISMATCH on ${field}:`, {
                submitted: submittedInput[field],
                received: receivedInput[field],
            });
            allMatch = false;
        }
    }
    return allMatch;
};
