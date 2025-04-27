## CLASSICAL AND QUANTUM CHAOS IN FUNDAMENTAL FIELD THEORIES

## Harald Markum and Rainer Pullirsch

## Atominstitut der ¨sterreichischen Universit¨ten o a Technische Universit¨t Wien a Wiedner Hauptstraße 8-10 A-1040 Vienna, Austria

Abstract. An investigation of classical chaos and quantum chaos in gauge fields and fermion fields, respectively, is presented for (quantum) electrodynamics. We analyze the leading Lyapunov exponents of U(1) gauge field configurations on a 12 3 lattice which are initialized by Monte Carlo simulations. We find that configurations in the strong coupling phase are substantially more chaotic than in the deconfinement phase. Considering the quantum case, complete eigenvalue spectra of the Dirac operator in quenched 4 d compact QED are studied on 8 3 × 4 and 8 3 × 6 lattices. We investigate the behavior of the nearest-neighbor spacing distribution P s ( ) as a measure of the fluctuation properties of the eigenvalues in the strong coupling and the Coulomb phase. In both phases we find agreement with the Wigner surmise of the unitary ensemble of random-matrix theory indicating quantum chaos.

## 1. Lyapunov exponents in Minkowskian U(1) gauge theory.

## 1.1. Classical chaotic dynamics from Monte Carlo initial states. Cha-

otic dynamics in general is characterized by the spectrum of Lyapunov exponents. These exponents, if they are positive, reflect an exponential divergence of initially adjacent configurations. In case of symmetries inherent in the Hamiltonian of the system there are corresponding zero values of these exponents. Finally negative exponents belong to irrelevant directions in the phase space: perturbation components in these directions die out exponentially. Pure gauge fields on the lattice show a characteristic Lyapunov spectrum consisting of one third of each kind of exponents [1]. Assuming this general structure of the Lyapunov spectrum we investigate presently its magnitude only, namely the maximal value of the Lyapunov exponent, L max .

The general definition of the Lyapunov exponent is based on a distance measure d t ( ) in phase space,

<!-- formula-not-decoded -->

In case of conservative dynamics the sum of all Lyapunov exponents is zero according to Liouville's theorem, ∑ L i = 0. We utilize the gauge invariant

1991 Mathematics Subject Classification. Primary: 70H05, 81T25 Secondary:

Key words and phrases.

Gauge theories, classical chaos, quantum chaos.

distance measure consisting of the local differences of energy densities between two 3 d field configurations on the lattice:

<!-- formula-not-decoded -->

Here the symbol ∑ P stands for the sum over all N P plaquettes, so this distance is bound in the interval (0 , 2 N ) for the group SU(N). U P and U ′ P are the plaquette variables, constructed from the basic link variables U x,i ,

<!-- formula-not-decoded -->

located on lattice links pointing from the position x = ( x , x 1 2 , x 3 ) to x + ae i . The generators of the group are T c = -igτ c / 2 with τ c being the Pauli matrices in case of SU(2) and A c x,i is the vector potential. The elementary plaquette variable is constructed for a plaquette with a corner at x and lying in the ij -plane as U x,ij = U x,i U x + i,j U † x + j,i U † x,j . It is related to the magnetic field strength B c x,k :

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

The electric field strength E c x,i is related to the canonically conjugate momentum P x,i = ˙ U x,i via

The Hamiltonian of the lattice gauge field system can be casted into the form

Here the scalar product stands for 〈 A, B 〉 = 1 2 tr( AB † ). The staple variable V is a sum of triple products of elementary link variables closing a plaquette with the chosen link U . This way the Hamiltonian is formally written as a sum over link contributions and V plays the role of the classical force acting on the link variable U .

<!-- formula-not-decoded -->

Initial conditions chosen randomly with a given average magnetic energy per plaquette have been investigated in past years [2]. We prepare the initial field configurations from a standard four dimensional Euclidean Monte Carlo program on a 12 3 × 4 lattice varying the gauge coupling g [3]. We relate such four dimensional Euclidean lattice field configurations to Minkowskian momenta and fields for the three dimensional Hamiltonian simulation by identifying a fixed time slice of the four dimensional lattice.

- 1.2. Chaos, confinement and continuum limit. We start the presentation of our results with a characteristic example of the time evolution of the distance between initially adjacent configurations. An initial state prepared by a standard four dimensional Monte Carlo simulation is evolved according to the classical Hamiltonian dynamics in real time. Afterwards this initial state is rotated locally by group elements which are chosen randomly near to the

Figure 1. Exponentially diverging distance in real time of initially adjacent U(1) field configurations on a 12 3 lattice prepared at β = 0 9 in the confinement (left) and at . β = 1 1 in the . Coulomb phase (right).

<!-- image -->

<!-- image -->

unity. The time evolution of this slightly rotated configuration is then pursued and finally the distance between these two evolutions is calculated at the corresponding times. A typical exponential rise of this distance followed by a saturation can be inspected in Fig. 1 from an example of U(1) gauge theory for two values of β = 1 /g 2 in the confinement phase and in the Coulomb phase. While the saturation is an artifact of the compact distance measure of the lattice, the exponential rise (the linear rise of the logarithm) can be used for the determination of the leading Lyapunov exponent. The left plot exhibits that in the confinement phase the field has larger Lyapunov exponents than in the Coulomb phase shown in the right plot.

The main result of the present study is the dependence of the leading Lyapunov exponent L max on the inverse coupling strength β , displayed in Fig. 2. As expected the strong coupling phase is more chaotic. The transition reflects the critical coupling to the Coulomb phase.

An interesting result concerning the continuum limit can be viewed from Fig. 3 which shows the energy dependence of the Lyapunov exponents for the U(1) theory. One observes an approximately quadratic relation in the weak coupling regime. From scaling arguments one expects a functional relationship between the Lyapunov exponent and the energy [1, 4]

<!-- formula-not-decoded -->

with the exponent k being crucial for the continuum limit of the classical field theory. A value of k &lt; 1 leads to a divergent Lyapunov exponent, while k &gt; 1 yields a vanishing L in the continuum. The case k = 1 is special allowing for a finite non-zero Lyapunov exponent. Our analysis of the scaling relation (7)

Figure 2. Lyapunov exponents of 100 U(1) field configurations as a function of coupling.

<!-- image -->

Figure 3. Average maximal Lyapunov exponent as a function of the scaled average energy per plaquette ag E 2 . The U(1) gauge theory shows an approximately quadratic behavior in the weak coupling regime.

<!-- image -->

gives evidence that the classical compact U(1) lattice gauge theory has k ≈ 2 and with L a ( ) → 0 a regular continuum theory.

## 2. Quantum chaos in compact Euclidean QED.

- 2.1. Manifestation of quantum chaos. The fluctuation properties of the eigenvalues of Dirac operator for quantum chromodynamics (QCD) on a lattice in Euclidean space-time have attracted much attention in the past few years. In Ref. [5] it was first shown for SU(2) lattice gauge theory that certain features of the spectrum of the Dirac operator are described by random-matrix theory (RMT). In particular the so-called nearest-neighbor spacing distribution P s ( ), i.e. the distribution of the spacings s of adjacent eigenvalues on

the 'unfolded' scale, agrees with the Wigner surmise of RMT. According to the Bohigas-Giannoni-Schmit conjecture [6], quantum systems whose classical counterparts are chaotic have a P s ( ) given by RMT whereas systems whose classical counterparts are integrable obey a Poisson distribution P s ( ) = e -s . Therefore, the specific form of P s ( ) is often taken as a criterion for 'quantum chaos'. However, there is no accepted proof of the Bohigas-Giannoni-Schmit conjecture yet. The field of quantum chaos is still developing and there are many open conceptual problems [7]. Applying this conjecture it was recently demonstrated that QCD is chaotic, both in the confinement and the quark gluon plasma phase [8].

A number of interesting results have been established for chaotic dynamics in classical gauge theories. Lattice gauge theories are chaotic as classical Hamiltonian dynamical systems [2]. Furthermore, it was found that the leading Lyapunov exponent of SU(2) Yang-Mills field configurations indicates that configurations corresponding to the deconfinement phase are chaotic although they are less chaotic than in the strong coupling phase at finite temperature [3]. The scaling of the maximal Lyapunov exponent in the classical continuum limit was studied in Ref. [4]: It was suggested that Abelian gauge theories behave regularly in the continuum limit whereas non-Abelian gauge theories are chaotic in the continuum, although the exact scaling relation is still an open problem. Chaos to order transitions were observed in a spatially homogeneous SU(2) Yang-Mills-Higgs system and in a spatially homogeneous SU(2) YangMills Chern-Simons Higgs system [9, 10]. In Ref. [9] a chaos to order transition was also seen on the quantum level, i.e. a smooth transition from a Wigner to a Poisson distribution was found. A transition in P s ( ) from Wigner to Poisson behavior was further observed at the metal-insulator transition of the Anderson model [11]. Further, the suppression of the characteristic manifestations of dynamical chaos by quantum fluctuations was analyzed in the context of spatially homogeneous scalar electrodynamics [12] and for a 0 + 1-dimensional space-time N -component φ 4 theory in the presence of an external field [13]. These chaos to order transitions were seen in spatially homogeneous models and not for the full classical field theory. The relationship to properties of the quantum field theory is an interesting issue.

Here we focus on the Dirac operator for quenched 4 d compact quantum electrodynamics (QED) to search for the possible existence of a transition from chaotic to regular behavior in Abelian lattice gauge theories. In particular, we are interested in the nearest-neighbor spacing distribution of the eigenvalues of the Dirac operator across the phase transition from the strong coupling to the Coulomb phase. In the strong coupling region Abelian as well as nonAbelian lattice gauge theories are in a confined phase [14]. For compact QED this means that for couplings β &lt; β c ≈ 1 01 the electron is confined. . However, when crossing the phase transition the conventional Coulomb phase is observed. It is an interesting question if the difference between the Coulomb

phase in QED and the quark-gluon plasma phase in QCD has an influence on the level repulsion of the corresponding Dirac spectra.

- 2.2. Quantum chaos of fermion fields. We generated gauge field configurations using the standard Wilson plaquette action for U(1) gauge theory,

<!-- formula-not-decoded -->

where U l ≡ U x,µ = exp( Θ i x,µ ), with Θ x,µ ∈ [ -π, π ), are the field variables defined on the links l ≡ ( x, µ ). The plaquette angles are Θ P = Θ x,µ +Θ x +ˆ µ,ν -Θ x +ˆ ν,µ -Θ x,ν . We simulated 8 3 × 4 and 8 3 × 6 lattices at various values of the inverse gauge coupling β = 1 /g 2 both in the strong coupling and the Coulomb phase. Typically we discarded the first 10000 sweeps for reaching equilibrium and produced 20 independent configurations separated by 1000 sweeps for each β . Because of the spectral ergodicity property of RMT one can replace ensemble averages by spectral averages [15] if one is only interested in the bulk properties. Thus a few independent configurations are sufficient to compute P s ( ).

On the Euclidean lattice the Dirac operator / D = / ∂ + ig / A for staggered fermions

<!-- formula-not-decoded -->

is anti-Hermitian so that all eigenvalues are imaginary. For convenience we denote them by iλ n and refer to the λ n as the eigenvalues in the following. Because of { / , γ D 5 } = 0 the λ n occur in pairs of opposite sign. All spectra were checked against the analytical sum rules

<!-- formula-not-decoded -->

where V is the lattice volume.

In RMT one has to distinguish between different universality classes which are determined by the symmetries of the system. So far the classification for the QED Dirac operator has not been done. Our calculations show that in the case of the staggered 4 d compact QED Dirac matrix the appropriate ensemble is the unitary ensemble. Although from a mathematical point of view this is the simplest one, the RMT result for the nearest-neighbor spacing distribution is still rather complicated. It can be expressed in terms of socalled prolate spheroidal functions, see Ref. [16] where P s ( ) has also been tabulated. A good approximation to P s ( ) is provided by the Wigner surmise for the unitary ensemble

<!-- formula-not-decoded -->

We have simulated 8 3 × 4 lattices at β = 0 , 0 90 . , 0 95 . , 1 00 . , 1 05 . , 1 10 . , 1 50 . and 8 3 × 6 lattices at β = 0 90 . , 1 10 . , 1 50. . All results are similar to those

Figure 4. Nearest-neighbor spacing distribution P s ( ) of the Dirac operator for compact U(1) theory in the strong coupling phase for β = 0 90 (left) and in the Coulomb phase for . β = 1 10 (right). . The histogram represents the lattice data on an 8 3 × 6 lattice averaged over 20 independent configurations. The full curve is the Wigner distribution of Eq. (11) for the unitary ensemble of RMT. For comparison the Poisson distribution P s ( ) = e -s is also indicated by the dashed line.

<!-- image -->

<!-- image -->

Figure 5. Nearest-neighbor spacing distribution P s ( ) of the analytically calculated eigenvalues of Eq. (12) for a free Dirac operator on a 53 × 47 × 43 × 41 lattice (histogram) compared with the Poisson distribution P s ( ) = e -s (solid line).

<!-- image -->

selected for the plots. The left plot in Fig. 4 shows the nearest-neighbor spacing distribution P s ( ) for β = 0 90 in the confined . phase averaged over 20 independent configurations on the 8 3 × 6 lattice compared with the Wigner surmise for the unitary ensemble of RMT of Eq. (11). Good agreement is found. According to the Bohigas-Giannoni-Schmit conjecture this means the

system can be regarded as chaotic in the strong coupling region. The right plot in Fig. 4 shows the nearest-neighbor spacing distribution P s ( ) for β = 1 10 . in the Coulomb phase again averaged over 20 independent configurations and compared with the Wigner surmise (11). The agreement of the lattice data with the RMT predictions is interpreted as a signal that quantum chaos survives the phase transition. We find no deviation up to the maximum coupling considered, β = 1 50. .

In the strong coupling phase the result holds down to β = 0. Therefore, we tend to interpret our, as well as previous [8, 5], results in the sense that the disorder of the gauge field configurations [2, 3] is responsible for the chaotic characteristics of the spectrum of the Dirac operator. In contrast to that: The free fermion theory is non-chaotic and the corresponding nearest-neighbor spacing distribution obeys a Poisson distribution. This is illustrated in Fig. 5 where P s ( ) is obtained from the analytical eigenvalues of the free Dirac operator on a 53 × 47 × 43 × 41 lattice:

<!-- formula-not-decoded -->

Here a is the lattice constant, L µ is the number of lattice sites in µ -direction, and n µ = 0 , ..., L µ -1. We used an asymmetric lattice with L µ being primes and restricted the range to ( L µ -1) / 2 instead of L µ -1 in each direction to avoid degeneracies of the free spectrum.

3. Conclusion. In the underlying article we performed a comparison of classical chaos and quantum chaos in fundamental field theories of physics, exemplified for the U(1) theory of electrodynamics. This is not a direct comparison, however, since it deals with the gauge field in classical theory and with fermions in the quantum case. It turned out that the classical U(1) field is chaotic in the confinement phase with decreasing Lyapunov exponents towards the Coulomb phase. A scaling analysis indicates a regular continuum theory as one expects from the Maxwell equations. On the other hand, our investigation of the quantized fermion field fulfills the criterion for quantum chaos both in the confinement and Coulomb phase. A scaling analysis was not possible for the quantum case (due to the lack of a β -function) which could cover the transition to a regular theory. Nevertheless, the free Dirac operator, in absence of a covariant derivative and minimal gauge coupling, exhibits regular behavior.

It would be interesting to study the direct counterpart of the classical gauge field after quantization. A similarly accurate determination of the eigenvalue spectrum of the gauge sector necessitates to construct the corresponding Fock space and to diagonalize high-dimensional matrices which seems to be out of reach for 4 d QED/QCD. On the other hand, chaos studies of the classical limit of the fermion field would also be of interest but have not yet been attempted.

Acknowledgments. This work has been supported by the Austrian National Scientific Fund under the project FWF P14435-TPH. We thank Bernd A. Berg, Tam´s S. Bir´, Natascha H¨rmann and Wolfgang Sakuler for previous a o o cooperations.

## REFERENCES

- [1] T.S. Bir´, S.G. Matinyan, and B. M¨ller, o u Chaos and Gauge Field Theory (World Scientific, Singapore, 1995).
- [2] T.S. Bir´, C. Gong, B. M¨ller, and A. Trayanov, Int. J. Mod. Phys. C5 (1994) 113. o u
- [3] T.S. Bir´, M. Feurstein, and H. Markum, APH Heavy Ion Physics 7 (1998) 235; T.S. o Bir´, N. H¨rmann, H. Markum, and R. Pullirsch, Nucl. Phys. B (Proc. Suppl.) 86 (2000) o o 403; H. Markum, R. Pullirsch, and W. Sakuler, hep-lat/0201001; hep-lat/0205003; hep-lat/0209039.
- [4] L. Casetti, R. Gatto, and M. Pettini, J. Phys. A32 (1999) 3055; H.B. Nielsen, H.H. Rugh, and S.E. Rugh, ICHEP96 1603, hep-th/9611128; B. M¨ller, chao-dyn/9607001; u H.B. Nielsen, H.H. Rugh, and S.E. Rugh, chao-dyn/9605013.
- [5] M.A. Halasz and J.J.M. Verbaarschot, Phys. Rev. Lett. 74 (1995) 3920; M.A. Halasz, T. Kalkreuter, and J.J.M. Verbaarschot, Nucl. Phys. B (Proc. Suppl.) 53 (1997) 266.
- [6] O. Bohigas, M.-J. Giannoni, and C. Schmit, Phys. Rev. Lett. 52 (1984) 1; O. Bohigas and M.-J. Giannoni, Springer Lect. Notes Phys. 209 (1984) 1.
- [7] Reviews on the subject of quantum chaos are: M.C. Gutzwiller, Chaos in Classical and Quantum Mechanics (Springer, New York, 1990); Proceedings of the LII Session of the Les Houches School, Chaos and Quantum Physics , edited by M.-J. Giannoni and A. Voros (North-Holland, Amsterdam, 1991); Quantum Chaos: Between Order and Disorder , edited by G. Casati and B.V. Chirikov (Cambridge Univ. Press, Cambridge, 1995).
- [8] R. Pullirsch, K. Rabitsch, T. Wettig, and H. Markum, Phys. Lett. B427 (1998) 119; H. Markum, R. Pullirsch, and T. Wettig, Phys. Rev. Lett. 83 (1999) 484; B.A. Berg, H. Markum, and R. Pullirsch, Phys. Rev. D59 (1999) 097504.
- [9] L. Salasnich, Mod. Phys. Lett. A12 (1997) 1473.
- [10] C. Mukku, M.S. Sriram, J. Segar, B.A. Bambah, and S. Lakshmibala, J. Phys. A30 (1997) 3003.
- [11] B.L. Al'tshuler, I.Kh. Zharekeshev, S.A. Kotochigova, and B.I. Shklovski˘ ı, Zh. Eksp. Teor. Fiz. 94 (1988) 343 [Sov. Phys. JETP 67 (1988) 625]; B.I. Shklovski˘ ı, B. Shapiro, B.R. Sears, P. Lambrianides, and H.B. Shore, Phys. Rev. B47 (1993) 11487.
- [12] S.G. Matinyan and B. M¨ller, Phys. Rev. Lett. 78 (1997) 2515. u
- [13] L. Casetti, R. Gatto, and M. Modugno, Phys. Rev. E57 (1998) 1223.
- [14] K.G. Wilson, Phys. Rev. D10 (1974) 2445.
- [15] T. Guhr, A. M¨ller-Groeling, and H.A. Weidenm¨ller, Phys. Rep. 299 (1998) 189; J.B. u u French, P.A. Mello, and A. Pandey, Phys. Lett. 80B (1978) 17.
- [16] M.L. Mehta, Random Matrices , 2nd ed. (Academic Press, San Diego, 1991).